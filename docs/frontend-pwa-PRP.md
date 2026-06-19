# PRP: PerX Frontend PWA — Implementation Blueprint

## Context

Three-portal React PWA (employee, employer, provider) built with Vite + TypeScript + Three.js/R3F + Tailwind + Framer Motion. The 3D Benefit Globe is the primary visual differentiator for the hackathon demo. Offline support via Workbox Service Worker + Dexie.js IndexedDB. Push notifications via the Web Push API.

## Goal

A PWA that works installably on mobile, supports offline perk browsing, delivers push notifications for approval events, and features a Three.js benefit globe as the employee home screen centerpiece.

---

## Key Frontend Architecture Decisions

### Routing Strategy
Single-origin app, role-based portal switching at `/employee/*`, `/employer/*`, `/provider/*`. After login, redirect to correct portal based on `role` in JWT payload.

### State Management
- **Zustand**: UI state, current user, filters, wishlist optimistic updates
- **TanStack Query v5**: Server state, API data fetching, caching, background refetch
- **Dexie.js**: Offline-first persistence (IndexedDB)

### API Client
Auto-generated TypeScript client from FastAPI's OpenAPI JSON using `openapi-typescript`. Never write API calls manually.

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/types.ts
```

Then use `fetch` with typed responses:
```typescript
// src/api/client.ts
import createClient from 'openapi-fetch';
import type { paths } from './types';

export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_URL });
```

---

## Implementation Plan

### Step 1: Vite PWA Config

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.png'],
      manifest: {
        name: 'PerX Benefits',
        short_name: 'PerX',
        description: 'Your personalized employee benefits marketplace',
        theme_color: '#0F0F23',
        background_color: '#0F0F23',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            // App shell: cache-first
            urlPattern: /^https:\/\/api\.perx\./,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 5,
              expiration: { maxAgeSeconds: 3600 },
              cacheableResponse: { statuses: [200] }
            }
          },
          {
            // Perk images: cache-first with long TTL
            urlPattern: /\.(?:png|jpg|jpeg|webp|avif)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: { maxAgeSeconds: 7 * 24 * 60 * 60, maxEntries: 200 }
            }
          }
        ]
      }
    })
  ]
});
```

**Validation:** `npm run build` → dist includes `sw.js` and `manifest.webmanifest`. Lighthouse PWA score ≥ 90.

---

### Step 2: IndexedDB Schema (Dexie.js)

```typescript
// src/db/index.ts
import Dexie, { Table } from 'dexie';

interface PerkRecord {
  id: string;
  name: string;
  category: string;
  employee_price_cents: number;
  short_description: string;
  image_url: string | null;
  tags: string[];
  provider_name: string;
  provider_logo: string | null;
  avg_rating: number;
  cached_at: number;  // Date.now() timestamp
}

interface RecommendationRecord {
  id: string;         // perk_id
  score: number;
  rank: number;
  reason_text: string;
  cached_at: number;
}

interface PendingAction {
  id: string;         // UUID for dedup
  type: 'interaction' | 'quick_add' | 'wishlist_add' | 'wishlist_remove';
  payload: object;
  created_at: number;
  retry_count: number;
}

interface BudgetCache {
  id: 'current';      // Always single record
  allocated_cents: number;
  spent_cents: number;
  remaining_cents: number;
  period: string;
  cached_at: number;
}

class PerxDB extends Dexie {
  perks!: Table<PerkRecord>;
  recommendations!: Table<RecommendationRecord>;
  pending_actions!: Table<PendingAction>;
  budget!: Table<BudgetCache>;

  constructor() {
    super('PerxDB');
    this.version(1).stores({
      perks: 'id, category, cached_at',
      recommendations: 'id, rank, cached_at',
      pending_actions: 'id, type, created_at',
      budget: 'id',
    });
  }
}

export const db = new PerxDB();
```

**Validation:** Open DevTools → Application → IndexedDB → PerxDB shows all tables after first load.

---

### Step 3: Background Sync (Offline Queue)

```typescript
// src/hooks/useOfflineActions.ts
import { db } from '../db';
import { api } from '../api/client';
import { v4 as uuidv4 } from 'uuid';

export function useOfflineActions() {
  const queueAction = async (type: PendingAction['type'], payload: object) => {
    await db.pending_actions.add({
      id: uuidv4(),
      type,
      payload,
      created_at: Date.now(),
      retry_count: 0,
    });
    
    // Try Background Sync API (Chrome/Android)
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const sw = await navigator.serviceWorker.ready;
      await sw.sync.register('sync-pending-actions');
    } else {
      // Fallback: try immediately
      await flushPendingActions();
    }
  };

  const flushPendingActions = async () => {
    const pending = await db.pending_actions.toArray();
    for (const action of pending) {
      try {
        if (action.type === 'interaction') {
          await api.POST('/api/v1/interactions', { body: action.payload });
        } else if (action.type === 'quick_add') {
          await api.POST('/api/v1/selections/quick-add', { body: action.payload });
        }
        // ... other types
        await db.pending_actions.delete(action.id);
      } catch {
        await db.pending_actions.update(action.id, { retry_count: action.retry_count + 1 });
      }
    }
  };

  return { queueAction, flushPendingActions };
}
```

```typescript
// src/sw/background-sync.ts (handled inside Service Worker)
self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'sync-pending-actions') {
    event.waitUntil(
      // Message the main thread to flush pending actions
      self.clients.matchAll().then(clients => {
        clients.forEach(client => client.postMessage({ type: 'FLUSH_PENDING_ACTIONS' }));
      })
    );
  }
});
```

---

### Step 4: The Benefit Globe (Three.js / R3F)

This is the hackathon's visual differentiator. Central employee avatar + 5-9 orbiting category nodes.

```typescript
// src/components/3d/BenefitGlobe.tsx
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Html, Float, Stars } from '@react-three/drei';
import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import * as THREE from 'three';

interface CategoryNode {
  category: string;
  score: number;
  perk_count: number;
  color: string;
  orbitRadius: number;
  orbitSpeed: number;
  orbitPhase: number;
}

const CATEGORY_CONFIG: Record<string, { color: string; emoji: string }> = {
  fitness:       { color: '#FF6B35', emoji: '🏃' },
  wellness:      { color: '#4ECDC4', emoji: '🧘' },
  food:          { color: '#FFE66D', emoji: '🍔' },
  travel:        { color: '#A8E6CF', emoji: '✈️' },
  education:     { color: '#C3A6FF', emoji: '📚' },
  entertainment: { color: '#FF8B94', emoji: '🎮' },
  transport:     { color: '#96E6A1', emoji: '🚲' },
  childcare:     { color: '#FFC3A0', emoji: '👶' },
};

function CategoryNodeMesh({ node, onClick }: { node: CategoryNode; onClick: () => void }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  
  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.elapsedTime * node.orbitSpeed + node.orbitPhase;
    meshRef.current.position.x = Math.cos(t) * node.orbitRadius;
    meshRef.current.position.z = Math.sin(t) * node.orbitRadius;
    meshRef.current.position.y = Math.sin(t * 0.5) * 0.5;  // Slight vertical wobble
    meshRef.current.rotation.y += 0.01;
  });
  
  const nodeSize = 0.2 + node.score * 0.3;  // Larger node = higher affinity
  
  return (
    <mesh
      ref={meshRef}
      onClick={onClick}
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
      scale={hovered ? 1.3 : 1}
    >
      <sphereGeometry args={[nodeSize, 16, 16]} />
      <meshStandardMaterial
        color={node.color}
        emissive={node.color}
        emissiveIntensity={hovered ? 0.8 : 0.3}
        roughness={0.2}
        metalness={0.8}
      />
      <Html distanceFactor={6} center>
        <div className="text-white text-xs font-medium bg-black/60 px-2 py-1 rounded-full backdrop-blur-sm whitespace-nowrap">
          {CATEGORY_CONFIG[node.category]?.emoji} {node.category}
          <span className="ml-1 text-white/60">{node.perk_count}</span>
        </div>
      </Html>
    </mesh>
  );
}

function CentralAvatar() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.2;
    }
  });
  
  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.4, 32, 32]} />
      <meshStandardMaterial color="#6366f1" emissive="#6366f1" emissiveIntensity={0.4} roughness={0.1} metalness={0.9} />
    </mesh>
  );
}

// Orbit rings for visual depth
function OrbitRing({ radius }: { radius: number }) {
  return (
    <mesh rotation={[Math.PI / 2, 0, 0]}>
      <ringGeometry args={[radius - 0.01, radius + 0.01, 64]} />
      <meshBasicMaterial color="#ffffff" opacity={0.05} transparent />
    </mesh>
  );
}

export function BenefitGlobe({ categories, onCategoryClick }: {
  categories: CategoryNode[];
  onCategoryClick: (category: string) => void;
}) {
  return (
    <div className="w-full h-[420px] rounded-2xl overflow-hidden bg-gradient-to-b from-slate-900 to-slate-950">
      <Canvas camera={{ position: [0, 2, 5], fov: 60 }}>
        <ambientLight intensity={0.3} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#6366f1" />
        
        <Stars radius={100} depth={50} count={2000} factor={3} fade />
        
        <CentralAvatar />
        
        {categories.map((node, i) => (
          <CategoryNodeMesh
            key={node.category}
            node={{ ...node, orbitRadius: 1.5 + (i % 3) * 0.4, orbitSpeed: 0.3 + i * 0.05, orbitPhase: (i / categories.length) * Math.PI * 2 }}
            onClick={() => onCategoryClick(node.category)}
          />
        ))}
        
        {[1.5, 1.9, 2.3].map((r) => <OrbitRing key={r} radius={r} />)}
        
        <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
      </Canvas>
    </div>
  );
}
```

**Usage in Employee Home:**
```typescript
// Fetch category data from /api/v1/recommendations/categories
// Render BenefitGlobe with onCategoryClick navigating to /employee/perks?category=X
```

---

### Step 5: Push Notification Setup

```typescript
// src/hooks/usePushNotifications.ts
const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY;

function urlB64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return new Uint8Array(rawData.split('').map(c => c.charCodeAt(0)));
}

export function usePushNotifications() {
  const subscribe = async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.log('Push not supported');
      return;
    }
    
    const sw = await navigator.serviceWorker.ready;
    let sub = await sw.pushManager.getSubscription();
    
    if (!sub) {
      sub = await sw.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlB64ToUint8Array(VAPID_PUBLIC_KEY)
      });
    }
    
    // Send subscription to backend
    await api.POST('/api/v1/auth/push-subscription', {
      body: {
        endpoint: sub.endpoint,
        keys: {
          p256dh: btoa(String.fromCharCode(...new Uint8Array(sub.getKey('p256dh')!))),
          auth: btoa(String.fromCharCode(...new Uint8Array(sub.getKey('auth')!))),
        }
      }
    });
  };

  return { subscribe };
}
```

```typescript
// src/sw/push-handler.ts (inside Service Worker)
self.addEventListener('push', (event: PushEvent) => {
  const data = event.data?.json() ?? {};
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/badge-72.png',
      data: data.data,
      actions: [
        { action: 'view', title: 'View' },
        { action: 'dismiss', title: 'Dismiss' }
      ]
    })
  );
});

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close();
  const url = event.notification.data?.url ?? '/employee/selections';
  event.waitUntil(
    self.clients.openWindow(url)
  );
});
```

---

### Step 6: Employer Dashboard — Real-Time Budget Ring

```typescript
// src/portals/employer/components/BudgetRing.tsx
import { motion } from 'framer-motion';

interface BudgetRingProps {
  allocated: number;
  spent: number;
  pending: number;
  remaining: number;
}

export function BudgetRing({ allocated, spent, pending, remaining }: BudgetRingProps) {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const spentPct = spent / allocated;
  const pendingPct = pending / allocated;
  
  return (
    <div className="relative flex items-center justify-center">
      <svg width="160" height="160" className="-rotate-90">
        {/* Background track */}
        <circle cx="80" cy="80" r={radius} fill="none" stroke="#1e293b" strokeWidth="12" />
        {/* Spent (solid) */}
        <motion.circle
          cx="80" cy="80" r={radius}
          fill="none" stroke="#6366f1" strokeWidth="12"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - spentPct) }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          strokeLinecap="round"
        />
        {/* Pending (dashed) */}
        <motion.circle
          cx="80" cy="80" r={radius}
          fill="none" stroke="#f59e0b" strokeWidth="8"
          strokeDasharray={`${circumference * pendingPct} ${circumference * (1 - pendingPct)}`}
          strokeDashoffset={circumference * (1 - spentPct)}
          opacity={0.7}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-2xl font-bold text-white">
          €{(remaining / 100).toFixed(0)}
        </div>
        <div className="text-xs text-slate-400">remaining</div>
      </div>
    </div>
  );
}
```

---

### Step 7: Perk Card with Framer Motion

```typescript
// src/components/ui/PerkCard.tsx
import { motion } from 'framer-motion';

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: { opacity: 1, y: 0, scale: 1 },
  hover: { y: -4, boxShadow: '0 20px 40px rgba(99, 102, 241, 0.15)' }
};

export function PerkCard({ perk, rank, onSelect, onWishlist }: PerkCardProps) {
  return (
    <motion.div
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      transition={{ duration: 0.3, delay: rank * 0.05 }}  // Staggered entrance
      className="bg-slate-800/60 rounded-2xl overflow-hidden border border-slate-700/50 backdrop-blur-sm cursor-pointer"
    >
      {/* Image */}
      <div className="relative h-40 bg-slate-700">
        {perk.image_url ? (
          <img src={perk.image_url} alt={perk.name} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">
            {CATEGORY_EMOJI[perk.category] ?? '🎁'}
          </div>
        )}
        {/* Recommendation reason pill */}
        {perk.reason_text && (
          <div className="absolute top-2 left-2 text-xs bg-indigo-600/90 text-white px-2 py-1 rounded-full backdrop-blur-sm">
            ✨ {perk.reason_text}
          </div>
        )}
      </div>
      
      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs text-indigo-400 font-medium uppercase tracking-wide">{perk.category}</p>
            <h3 className="text-white font-semibold leading-tight mt-0.5">{perk.name}</h3>
            <p className="text-slate-400 text-sm mt-1 line-clamp-2">{perk.short_description}</p>
          </div>
          <div className="text-right shrink-0">
            <div className="text-xl font-bold text-white">€{(perk.employee_price_cents / 100).toFixed(0)}</div>
            <div className="text-xs text-slate-500">/month</div>
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => onSelect(perk)}
            className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2 rounded-xl transition-colors"
          >
            Add to Benefits
          </motion.button>
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => onWishlist(perk)}
            className="p-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl transition-colors"
          >
            ♡
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}
```

---

## PWA Offline Strategy Summary

| URL Pattern | Strategy | Offline Fallback |
|-------------|----------|-----------------|
| App shell (HTML/JS/CSS) | Cache First | ✅ Always works |
| `/api/v1/recommendations` | Network First, 5s timeout | IndexedDB cached recommendations |
| `/api/v1/perks` | Network First | IndexedDB cached perk catalog |
| `/api/v1/me/budget` | Network First | IndexedDB cached budget |
| Perk images | Cache First, 7d TTL | Placeholder SVG |
| POST requests (interactions, selections) | Background Sync queue | Pending actions table |

---

## Environment Variables

```bash
# .env (frontend)
VITE_API_URL=http://localhost:8000
VITE_VAPID_PUBLIC_KEY=BN...  # Generate with: npx web-push generate-vapid-keys

# .env (backend)
DATABASE_URL=postgresql+asyncpg://perx:perx@postgres:5432/perx
REDIS_URL=redis://redis:6379/0
JWT_SECRET=your-very-long-secret-key-here
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma2:2b
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
VAPID_CLAIMS_EMAIL=admin@perxchallenge.com
```

## Anti-Patterns

- **DO NOT** use `localStorage` for the offline perk store — Dexie.js (IndexedDB) only.
- **DO NOT** store the JWT in localStorage — use `httpOnly` cookies in production; for hackathon, use memory store (Zustand) + refresh token in IndexedDB.
- **DO NOT** make Globe component re-render on every recommendation score update — memoize category data with `useMemo`.
- **DO NOT** log interactions synchronously — always use `useOfflineActions` hook which handles both online and offline cases.
- **DO NOT** show prices in Euros directly from API cents — always use a `formatCents(cents)` utility: `(cents / 100).toFixed(2)`.
