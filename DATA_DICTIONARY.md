\# YottaFlex Cold Chain Monitoring System

\## Data Dictionary



This document describes the database entities, columns, data types, constraints, and relationships.



\### 1. Product

| Field | Type | Constraint / Description |

|---|---|---|

| product\_id | TEXT | Primary Key |

| product\_name | TEXT | Required |

| product\_category | TEXT | Required |

| min\_temperature | REAL | Required, minimum temperature in Â°C |

| max\_temperature | REAL | Required, maximum temperature in Â°C |

| min\_humidity | REAL | Optional, minimum humidity in % |

| max\_humidity | REAL | Optional, maximum humidity in % |

| created\_at | TEXT | Required, creation timestamp |



\### 2. Shipment

| Field | Type | Constraint / Description |

|---|---|---|

| shipment\_id | TEXT | Primary Key |

| product\_id | TEXT | Required, FK â†’ Product |

| origin | TEXT | Required |

| destination | TEXT | Required |

| departure\_time | TEXT | Required |

| expected\_delivery\_time | TEXT | Optional |

| actual\_delivery\_time | TEXT | Optional |

| shipment\_status | TEXT | Required |

| created\_at | TEXT | Required |



\### 3. Container

| Field | Type | Constraint / Description |

|---|---|---|

| container\_id | TEXT | Primary Key |

| container\_type | TEXT | Required |

| capacity | REAL | Optional |

| capacity\_unit | TEXT | Optional |

| container\_status | TEXT | Required |

| last\_maintenance\_date | TEXT | Optional |

| created\_at | TEXT | Required |



\### 4. Sensor

| Field | Type | Constraint / Description |

|---|---|---|

| sensor\_id | TEXT | Primary Key |

| container\_id | TEXT | Required, FK â†’ Container |

| sensor\_type | TEXT | Required |

| measurement\_unit | TEXT | Required |

| calibration\_date | TEXT | Required |

| calibration\_due\_date | TEXT | Optional |

| sensor\_status | TEXT | Required |

| created\_at | TEXT | Required |



\### 5. SensorReading

| Field | Type | Constraint / Description |

|---|---|---|

| reading\_id | TEXT | Primary Key |

| sensor\_id | TEXT | Required, FK â†’ Sensor |

| recorded\_at | TEXT | Required |

| temperature | REAL | Optional, Â°C |

| humidity | REAL | Optional, % |

| battery\_level | REAL | Optional |

| signal\_strength | REAL | Optional |

| data\_quality | TEXT | Required |

&#x20;

Unique constraint: sensor\_id + recorded\_at.



\### 6. RouteStop

| Field | Type | Constraint / Description |

|---|---|---|

| route\_stop\_id | TEXT | Primary Key |

| shipment\_id | TEXT | Required, FK â†’ Shipment |

| stop\_sequence | INTEGER | Required |

| location\_name | TEXT | Required |

| planned\_arrival\_time | TEXT | Optional |

| actual\_arrival\_time | TEXT | Optional |

| planned\_departure\_time | TEXT | Optional |

| actual\_departure\_time | TEXT | Optional |

| stop\_status | TEXT | Required |



Unique constraint: shipment\_id + stop\_sequence.



\### 7. ThresholdPolicy

| Field | Type | Constraint / Description |

|---|---|---|

| policy\_id | TEXT | Primary Key |

| product\_id | TEXT | Required, FK â†’ Product |

| min\_temperature | REAL | Required, Â°C |

| max\_temperature | REAL | Required, Â°C |

| min\_humidity | REAL | Optional, % |

| max\_humidity | REAL | Optional, % |

| max\_excursion\_minutes | INTEGER | Required |

| effective\_from | TEXT | Required |

| effective\_to | TEXT | Optional |

| created\_at | TEXT | Required |



Checks: minimum temperature must be less than maximum temperature. Humidity limits must be ordered when both are provided.



\### 8. Excursion

| Field | Type | Constraint / Description |

|---|---|---|

| excursion\_id | TEXT | Primary Key |

| shipment\_id | TEXT | Required, FK â†’ Shipment |

| sensor\_id | TEXT | Required, FK â†’ Sensor |

| policy\_id | TEXT | Required, FK â†’ ThresholdPolicy |

| excursion\_type | TEXT | Required |

| start\_time | TEXT | Required |

| end\_time | TEXT | Optional |

| duration\_minutes | REAL | Optional |

| observed\_min\_value | REAL | Optional |

| observed\_max\_value | REAL | Optional |

| severity | TEXT | Required |

| excursion\_status | TEXT | Required |

| ground\_truth | INTEGER | Defaults to 0; only 0 or 1 |

| created\_at | TEXT | Required |



\### 9. CustodyEvent

| Field | Type | Constraint / Description |

|---|---|---|

| custody\_event\_id | TEXT | Primary Key |

| shipment\_id | TEXT | Required, FK â†’ Shipment |

| event\_type | TEXT | Required |

| handled\_by | TEXT | Required |

| location | TEXT | Required |

| event\_time | TEXT | Required |

| remarks | TEXT | Optional |

| created\_at | TEXT | Required |



\### 10. CorrectiveAction

| Field | Type | Constraint / Description |

|---|---|---|

| action\_id | TEXT | Primary Key |

| excursion\_id | TEXT | Required, FK â†’ Excursion |

| action\_type | TEXT | Required |

| description | TEXT | Required |

| assigned\_to | TEXT | Optional |

| action\_status | TEXT | Required |

| started\_at | TEXT | Optional |

| completed\_at | TEXT | Optional |

| outcome | TEXT | Optional |

| created\_at | TEXT | Required |



\### 11. ShipmentContainer (Bridge Table)

| Field | Type | Constraint / Description |

|---|---|---|

| assignment\_id | TEXT | Primary Key |

| shipment\_id | TEXT | Required, FK â†’ Shipment |

| container\_id | TEXT | Required, FK â†’ Container |

| assigned\_at | TEXT | Required |

| released\_at | TEXT | Optional |



Unique constraint: shipment\_id + container\_id + assigned\_at.



\### Relationships

\- Product 1:N Shipment

\- Product 1:N ThresholdPolicy

\- Container 1:N Sensor

\- Sensor 1:N SensorReading

\- Shipment 1:N RouteStop

\- Shipment 1:N CustodyEvent

\- Shipment 1:N Excursion

\- Sensor 1:N Excursion

\- ThresholdPolicy 1:N Excursion

\- Excursion 1:N CorrectiveAction

\- Shipment N:M Container through ShipmentContainer



\### Notes

\- Primary keys uniquely identify records.

\- Foreign keys maintain parent-child relationships.

\- Optional fields are nullable unless otherwise constrained.

\- Temperature is measured in degrees Celsius (Â°C).

\- Humidity is represented as a percentage (%).

\- Timestamp fields are stored as TEXT in the database.

\- Allowed status values and enumerations should be documented from the generator/application logic; they are not enforced as SQL CHECK constraints in the current schema.
