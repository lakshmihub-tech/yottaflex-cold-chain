PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Product (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL,
    min_temperature REAL NOT NULL,
    max_temperature REAL NOT NULL,
    min_humidity REAL,
    max_humidity REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Shipment (
    shipment_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    expected_delivery_time TEXT,
    actual_delivery_time TEXT,
    shipment_status TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id)
);
CREATE TABLE IF NOT EXISTS Container (
    container_id TEXT PRIMARY KEY,
    container_type TEXT NOT NULL,
    capacity REAL,
    capacity_unit TEXT,
    container_status TEXT NOT NULL,
    last_maintenance_date TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Sensor (
    sensor_id TEXT PRIMARY KEY,
    container_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    measurement_unit TEXT NOT NULL,
    calibration_date TEXT NOT NULL,
    calibration_due_date TEXT,
    sensor_status TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY (container_id)
        REFERENCES Container(container_id)
);
CREATE TABLE IF NOT EXISTS SensorReading (
    reading_id TEXT PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    battery_level REAL,
    signal_strength REAL,
    data_quality TEXT NOT NULL,

    FOREIGN KEY (sensor_id)
        REFERENCES Sensor(sensor_id),

    UNIQUE (sensor_id, recorded_at)
);
CREATE TABLE IF NOT EXISTS RouteStop (
    route_stop_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    stop_sequence INTEGER NOT NULL,
    location_name TEXT NOT NULL,
    planned_arrival_time TEXT,
    actual_arrival_time TEXT,
    planned_departure_time TEXT,
    actual_departure_time TEXT,
    stop_status TEXT NOT NULL,

    FOREIGN KEY (shipment_id)
        REFERENCES Shipment(shipment_id),

    UNIQUE (shipment_id, stop_sequence)
);
CREATE TABLE IF NOT EXISTS ThresholdPolicy (
    policy_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    min_temperature REAL NOT NULL,
    max_temperature REAL NOT NULL,
    min_humidity REAL,
    max_humidity REAL,
    max_excursion_minutes INTEGER NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    CHECK (min_temperature < max_temperature),
    CHECK (
        min_humidity IS NULL
        OR max_humidity IS NULL
        OR min_humidity < max_humidity
    )
);
CREATE TABLE IF NOT EXISTS Excursion (
    excursion_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    excursion_type TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_minutes REAL,
    observed_min_value REAL,
    observed_max_value REAL,
    severity TEXT NOT NULL,
    excursion_status TEXT NOT NULL,
    ground_truth INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,

    FOREIGN KEY (shipment_id)
        REFERENCES Shipment(shipment_id),

    FOREIGN KEY (sensor_id)
        REFERENCES Sensor(sensor_id),

    FOREIGN KEY (policy_id)
        REFERENCES ThresholdPolicy(policy_id),

    CHECK (ground_truth IN (0, 1))
);
CREATE TABLE IF NOT EXISTS CustodyEvent (
    custody_event_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    handled_by TEXT NOT NULL,
    location TEXT NOT NULL,
    event_time TEXT NOT NULL,
    remarks TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY (shipment_id)
        REFERENCES Shipment(shipment_id)
);
CREATE TABLE IF NOT EXISTS CorrectiveAction (
    action_id TEXT PRIMARY KEY,
    excursion_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    assigned_to TEXT,
    action_status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    outcome TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY (excursion_id)
        REFERENCES Excursion(excursion_id)
);
CREATE TABLE IF NOT EXISTS ShipmentContainer (
    assignment_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    container_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    released_at TEXT,

    FOREIGN KEY (shipment_id)
        REFERENCES Shipment(shipment_id),

    FOREIGN KEY (container_id)
        REFERENCES Container(container_id),

    UNIQUE (shipment_id, container_id, assigned_at)
);