-- Fix interaction_count trigger: enum value is 'redeem', not 'redeemed'.

CREATE OR REPLACE FUNCTION update_employee_interaction_count() RETURNS TRIGGER AS $$
DECLARE
    warm_threshold INTEGER;
BEGIN
    IF NEW.interaction_type NOT IN ('select', 'reject', 'add_to_wishlist', 'redeem') THEN
        RETURN NEW;
    END IF;

    warm_threshold := COALESCE(
        (SELECT current_setting('app.recommender_warm_threshold', TRUE))::INTEGER,
        10
    );

    UPDATE employee_profiles
    SET
        interaction_count = interaction_count + 1,
        recommender_mode = CASE
            WHEN (interaction_count + 1) >= warm_threshold THEN 'warm'
            ELSE recommender_mode
        END,
        updated_at = NOW()
    WHERE id = NEW.employee_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
