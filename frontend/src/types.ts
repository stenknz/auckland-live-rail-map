export interface RailRoute {
  route_id: string;
  short_name: string;
  long_name: string;
  color: string;
  text_color: string;
}

export interface RailStop {
  stop_id: string;
  name: string;
  lat: number;
  lon: number;
  platform: string | null;
}

export interface StaticNetwork {
  routes: RailRoute[];
  stops: RailStop[];
  shapes: Record<string, [number, number][]>;
  shape_routes: Record<string, string>;
}

export interface Vehicle {
  id: string;
  vehicle_id: string;
  vehicle_label: string | null;
  route_id: string | null;
  trip_id: string | null;
  nextStopId: string | null;
  nextStopName: string | null;
  latitude: number;
  longitude: number;
  bearing: number | null;
  timestamp: number | null;
  age_seconds: number | null;
  next_stop_id?: string | null;
  next_stop_name?: string | null;
}

export interface VehiclesResponse {
  generated_at: string;
  source_timestamp: number | null;
  filter_mode?: string;
  vehicles: Vehicle[];
  stale?: boolean;
  error?: string | null;
  last_update?: number | null;
}

export interface Arrival {
  trip_id: string;
  route_id: string | null;
  route_color: string;
  route_short_name: string;
  headsign: string;
  scheduled_time: string | null;
  realtime: boolean;
  estimated_time: string;
  delay_seconds: number | null;
  cancelled: boolean;
  platform: string | null;
}

export interface ArrivalsResponse {
  stop_id: string;
  stop_name: string | null;
  generated_at: string;
  arrivals: Arrival[];
  stale?: boolean;
  error?: string | null;
  last_update?: number | null;
}

export interface Alert {
  id: string;
  header: string | null;
  description: string | null;
  informed: { route_id: string | null; stop_id: string | null; agency_id: string | null }[];
  periods: { start: number | null; end: number | null }[];
  cause: number | null;
  effect: number | null;
}

export interface AlertsResponse {
  generated_at: string;
  source_timestamp: number | null;
  alerts: Alert[];
  stale?: boolean;
  error?: string | null;
  last_update?: number | null;
}

export interface StatusResponse {
  gtfs: { loaded: boolean; error: string | null; stops: number; routes: number };
  vehicles: { last_update: number | null; age_seconds: number | null; stale: boolean; error: string | null };
  trips: { last_update: number | null; age_seconds: number | null; stale: boolean; error: string | null };
  alerts: { last_update: number | null; age_seconds: number | null; stale: boolean; error: string | null };
  server_time: string;
}
