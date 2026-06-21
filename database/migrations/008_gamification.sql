-- Employee gamification: journey, quiz, achievements, reviews, XP/points/streak

CREATE TABLE IF NOT EXISTS achievements (
    slug VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    requirement TEXT NOT NULL,
    interactive BOOLEAN NOT NULL DEFAULT FALSE,
    goal INTEGER
);

INSERT INTO achievements (slug, title, description, requirement, interactive, goal) VALUES
    ('first-steps', 'Hapat e parë', 'Përfundo hapin e parë të rrugës së përfitimeve.', 'Përfundo çdo milestone udhëtimi', FALSE, NULL),
    ('globe-trotter', 'Eksplorues global', 'Eksploro përfitime në 4 kategori të ndryshme.', 'Vizito 4 kategori në Eksploro', FALSE, NULL),
    ('wishlist-curator', 'Kurues i të ruajturave', 'Shto 5 përfitime te të ruajturat.', '5 artikuj të ruajtur', FALSE, NULL),
    ('smart-spender', 'Zgjedhës i zgjuar', 'Zgjidh një përfitim me bonus pyetësorë.', 'Përfundo rrjedhën Pyetësorë + Zgjidh', FALSE, NULL),
    ('well-rounded', 'I balancuar', 'Përfundo të gjitha hapat e rrugës.', 'Të 4 hapat e rrugës', FALSE, NULL),
    ('budget-master', 'Mjeshtër buxheti', 'Mbaj përdorimin e buxhetit nën 80% për 3 muaj.', '3 muaj nën 80%', FALSE, NULL),
    ('marathoner', 'Maratonist', 'Regjistro 100 km aktiv drejt objektivit të fitnessit.', '100 km të regjistruara', TRUE, 100)
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS employee_gamification (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0,
    class_label VARCHAR(100) NOT NULL DEFAULT 'I ri',
    marathoner_miles INTEGER NOT NULL DEFAULT 0,
    last_active_date DATE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journey_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, category)
);

CREATE INDEX IF NOT EXISTS ix_journey_progress_user_id ON journey_progress(user_id);

CREATE TABLE IF NOT EXISTS quiz_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    score INTEGER NOT NULL,
    total INTEGER NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, category)
);

CREATE INDEX IF NOT EXISTS ix_quiz_scores_user_id ON quiz_scores(user_id);

CREATE TABLE IF NOT EXISTS employee_achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_slug VARCHAR(50) NOT NULL REFERENCES achievements(slug) ON DELETE CASCADE,
    unlocked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, achievement_slug)
);

CREATE INDEX IF NOT EXISTS ix_employee_achievements_user_id ON employee_achievements(user_id);

CREATE TABLE IF NOT EXISTS employee_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    perk_id UUID NOT NULL REFERENCES perks(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, perk_id)
);

CREATE INDEX IF NOT EXISTS ix_employee_reviews_user_id ON employee_reviews(user_id);
