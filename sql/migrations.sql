-- users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    phone VARCHAR(50),
    avatar_url TEXT,
    google_id VARCHAR(255) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    plan VARCHAR(50) DEFAULT 'trial',
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    razorpay_customer_id VARCHAR(255),
    notif_new_review BOOLEAN DEFAULT TRUE,
    notif_negative_alert BOOLEAN DEFAULT TRUE,
    whatsapp_alerts BOOLEAN DEFAULT FALSE,
    whatsapp_number VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- businesses
CREATE TABLE IF NOT EXISTS businesses (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER REFERENCES users(id),
    name VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    category VARCHAR(100),
    phone_number VARCHAR(50),
    whatsapp_number VARCHAR(50),
    owner_email VARCHAR(255),
    address TEXT,
    area_locality VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(20),
    place_id VARCHAR(255),
    google_review_url TEXT,
    google_rating NUMERIC(3, 2),
    review_count INTEGER,
    logo_url TEXT,
    primary_color VARCHAR(50) DEFAULT '#6366F1',
    tagline VARCHAR(255),
    welcome_message TEXT,
    menu_data JSONB,
    price_range VARCHAR(100),
    cuisine_speciality VARCHAR(100),
    dietary_options JSONB,
    signature_dish VARCHAR(255),
    highlighted_dishes TEXT,
    excluded_dishes TEXT,
    business_hours JSONB,
    animation_style VARCHAR(100) DEFAULT 'glow_float',
    particle_intensity INTEGER DEFAULT 5,
    seasonal_theme VARCHAR(100),
    review_language VARCHAR(50) DEFAULT 'english',
    ai_variant_count INTEGER DEFAULT 3,
    negative_filter_enabled BOOLEAN DEFAULT FALSE,
    onboarding_step INTEGER DEFAULT 0,
    is_onboarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- menu_items
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- qr_codes
CREATE TABLE IF NOT EXISTS qr_codes (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    label VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- scan_events
CREATE TABLE IF NOT EXISTS scan_events (
    id SERIAL PRIMARY KEY,
    qr_code_id INTEGER REFERENCES qr_codes(id),
    business_id INTEGER REFERENCES businesses(id),
    session_id VARCHAR(255) UNIQUE,
    stage VARCHAR(50) DEFAULT 'scanned',
    overall_rating INTEGER,
    food_rating INTEGER,
    service_rating INTEGER,
    atmosphere_rating INTEGER,
    selected_items TEXT[],
    meal_type VARCHAR(100),
    price_range VARCHAR(100),
    seating_type VARCHAR(100),
    wait_time VARCHAR(100),
    review_variant INTEGER,
    was_negative BOOLEAN DEFAULT FALSE,
    device_type VARCHAR(100),
    user_agent TEXT,
    ip_hash VARCHAR(255),
    hour_of_day INTEGER GENERATED ALWAYS AS (EXTRACT(HOUR FROM scanned_at)) STORED,
    day_of_week INTEGER GENERATED ALWAYS AS (EXTRACT(ISODOW FROM scanned_at)) STORED,
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- negative_feedback
CREATE TABLE IF NOT EXISTS negative_feedback (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    scan_event_id INTEGER REFERENCES scan_events(id),
    rating INTEGER,
    feedback_text TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- upgrade_requests
CREATE TABLE IF NOT EXISTS upgrade_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    business_name VARCHAR(255),
    contact_name VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    plan_requested VARCHAR(50),
    amount_paid INTEGER,
    utr_number VARCHAR(100),
    payment_method VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    admin_note TEXT,
    activated_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plan VARCHAR(50),
    status VARCHAR(50),
    razorpay_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    amount_paise INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- refresh_tokens
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token_hash VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
