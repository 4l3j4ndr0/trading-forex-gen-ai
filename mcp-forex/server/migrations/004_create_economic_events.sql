-- Economic events cache (calendar data)
CREATE TABLE economic_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time TIMESTAMPTZ NOT NULL,
    currency VARCHAR(5) NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    impact VARCHAR(10) NOT NULL,
    forecast VARCHAR(30),
    previous VARCHAR(30),
    actual VARCHAR(30),
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_time ON economic_events(event_time);
CREATE INDEX idx_events_impact ON economic_events(impact);
