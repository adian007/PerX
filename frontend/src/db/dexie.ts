import Dexie, { type EntityTable } from 'dexie'
import { DEFAULT_USER_STATE, type UserGamificationState } from '@/types'

interface UserStateRow {
  id: string
  state: UserGamificationState
}

class PerXDatabase extends Dexie {
  userState!: EntityTable<UserStateRow, 'id'>

  constructor() {
    super('PerXDB')
    this.version(1).stores({
      userState: 'id',
    })
  }
}

export const db = new PerXDatabase()

const STATE_KEY = 'default'

export async function loadUserStateFromDexie(): Promise<UserGamificationState | null> {
  const row = await db.userState.get(STATE_KEY)
  return row?.state ?? null
}

export async function saveUserStateToDexie(state: UserGamificationState): Promise<void> {
  await db.userState.put({ id: STATE_KEY, state })
}

export async function clearUserStateFromDexie(): Promise<void> {
  await db.userState.delete(STATE_KEY)
}

export async function resetUserStateInDexie(): Promise<UserGamificationState> {
  await clearUserStateFromDexie()
  await saveUserStateToDexie(DEFAULT_USER_STATE)
  return { ...DEFAULT_USER_STATE }
}
