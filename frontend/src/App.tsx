import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, Marker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  fetchStatic, fetchVehicles, fetchArrivals, fetchAlerts, fetchStatus,
} from "./api";
import type { StaticNetwork, Vehicle, Arrival, Alert, StatusResponse } from "./types";
import "./index.css";

const AUCKLAND_CENTER: [number, number] = [-36.85, 174.76];

export default function App() {
  const [network, setNetwork] = useState<StaticNetwork | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [selectedStop, setSelectedStop] = useState<string | null>(null);
  const [arrivals, setArrivals] = useState<Arrival[] | null>(null);
  const [arrivalsMeta, setArrivalsMeta] = useState<any>(null);
  const [enabledRoutes, setEnabledRoutes] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [vehiclesStale, setVehiclesStale] = useState(false);

  // initial static
  useEffect(() => {
    fetchStatic().then((d) => {
      setNetwork(d);
      setEnabledRoutes(new Set(d.routes.map((r: any) => r.route_id)));
    }).catch((e) => setError(String(e)));
  }, []);

  // poll vehicles
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await fetchVehicles();
        if (!alive) return;
        setVehicles(d.vehicles || []);
        setVehiclesStale(!!d.stale);
      } catch (e) {
        if (alive) setError(String(e));
      }
    };
    load();
    const iv = setInterval(load, 30000);
    return () => { alive = false; clearInterval(iv); };
  }, []);

  // poll alerts
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await fetchAlerts();
        if (alive) setAlerts(d.alerts || []);
      } catch { /* ignore */ }
    };
    load();
    const iv = setInterval(load, 60000);
    return () => { alive = false; clearInterval(iv); };
  }, []);

  // poll status
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await fetchStatus();
        if (alive) setStatus(d);
      } catch { /* ignore */ }
    };
    load();
    const iv = setInterval(load, 30000);
    return () => { alive = false; clearInterval(iv); };
  }, []);

  // arrivals when stop selected
  useEffect(() => {
    if (!selectedStop) { setArrivals(null); return; }
    let alive = true;
    const load = async () => {
      try {
        const d = await fetchArrivals(selectedStop);
        if (alive) { setArrivals(d.arrivals || []); setArrivalsMeta(d); }
      } catch (e) { if (alive) setError(String(e)); }
    };
    load();
    const iv = setInterval(load, 30000);
    return () => { alive = false; clearInterval(iv); };
  }, [selectedStop]);

  const routeMap = useMemo(() => {
    const m = new Map<string, any>();
    network?.routes.forEach((r) => m.set(r.route_id, r));
    return m;
  }, [network]);

  const filteredStops = useMemo(() => {
    if (!network) return [];
    const q = search.trim().toLowerCase();
    if (!q) return network.stops;
    return network.stops.filter((s) => s.name.toLowerCase().includes(q));
  }, [network, search]);

  // unique station markers by name+rounded coords
  const stationMarkers = useMemo(() => {
    if (!network) return [];
    const seen = new Set<string>();
    const out: any[] = [];
    for (const s of network.stops) {
      const key = `${s.name}|${s.lat.toFixed(4)}|${s.lon.toFixed(4)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(s);
    }
    return out;
  }, [network]);

  const shapesByRoute = useMemo(() => {
    if (!network) return new Map();
    const m = new Map<string, [number, number][][]>();
    for (const [shapeId, pts] of Object.entries(network.shapes)) {
      const rid = network.shape_routes[shapeId];
      if (!rid || !enabledRoutes.has(rid)) continue;
      if (!m.has(rid)) m.set(rid, []);
      m.get(rid)!.push(pts as [number, number][]);
    }
    return m;
  }, [network, enabledRoutes]);

  const filteredVehicles = useMemo(() => {
    return vehicles.filter((v) => !v.route_id || enabledRoutes.has(v.route_id));
  }, [vehicles, enabledRoutes]);

  const toggleRoute = (rid: string) => {
    setEnabledRoutes((prev) => {
      const n = new Set(prev);
      if (n.has(rid)) n.delete(rid); else n.add(rid);
      return n;
    });
  };

  return (
    <div className="app">
      <div className="topbar">
        <div className="title">Auckland Live Rail Map</div>
        <div className="status">
          {vehiclesStale ? <span className="error">stale vehicle data</span> : <span>live</span>}
          {status && <> · {status.vehicles.age_seconds ?? "—"}s ago · {filteredVehicles.length} trains</>}
        </div>
      </div>
      <aside className="sidebar">
        <div className="card">
          <div className="card-title">Lines</div>
          {network?.routes.map((r) => (
            <label key={r.route_id} className="line-filter">
              <input
                type="checkbox"
                checked={enabledRoutes.has(r.route_id)}
                onChange={() => toggleRoute(r.route_id)}
              />
              <span className="line-swatch" style={{ background: `#${r.color}` }} />
              <span>{r.short_name}</span>
              <span className="muted small">{r.long_name}</span>
            </label>
          ))}
        </div>
        <div className="card">
          <div className="card-title">Station search</div>
          <input
            type="search"
            placeholder="Search stations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div style={{ maxHeight: 200, overflow: "auto", marginTop: 8 }}>
            {filteredStops.slice(0, 40).map((s) => (
              <div
                key={s.stop_id}
                className="row"
                style={{ padding: "4px 0", cursor: "pointer" }}
                onClick={() => setSelectedStop(s.stop_id)}
              >
                <span className="small">{s.name}</span>
                <span className="muted small">{s.platform ? `P${s.platform}` : ""}</span>
              </div>
            ))}
            {filteredStops.length === 0 && <div className="empty">No stations</div>}
          </div>
        </div>
        <div className="card">
          <div className="card-title">
            {selectedStop ? (arrivalsMeta?.stop_name || selectedStop) : "Station detail"}
          </div>
          {!selectedStop && <div className="empty">Select a station to see arrivals.</div>}
          {selectedStop && arrivals === null && <div className="spinner">Loading…</div>}
          {selectedStop && arrivals && arrivals.length === 0 && <div className="empty">No upcoming services.</div>}
          {selectedStop && arrivals && arrivals.map((a, i) => (
            <div key={i} className="arrival-row">
              <div>
                <div style={{ fontWeight: 600 }}>
                  <span style={{ color: `#${a.route_color}` }}>{a.route_short_name}</span>{" "}
                  {a.headsign || "—"}
                </div>
                <div className="muted small">
                  {a.realtime ? (
                    <span className="badge rt">realtime</span>
                  ) : (
                    <span className="badge sched">scheduled</span>
                  )}
                  {a.delay_seconds ? ` · delay ${Math.round(a.delay_seconds / 60)}m` : ""}
                  {a.cancelled ? " · CANCELLED" : ""}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div>{new Date(a.estimated_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
                <div className="muted small">
                  {a.platform ? `P${a.platform}` : ""}
                </div>
              </div>
            </div>
          ))}
          {arrivalsMeta?.stale && <div className="error small">Stale arrival data</div>}
        </div>
        <div className="card">
          <div className="card-title">Service alerts</div>
          {alerts.length === 0 && <div className="empty">No active alerts.</div>}
          {alerts.slice(0, 8).map((a) => (
            <div key={a.id} className="alert-item">
              <div className="alert-header">{a.header || "Alert"}</div>
              <div className="muted small">{a.description}</div>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="card-title">Data status</div>
          {error && <div className="error">{error}</div>}
          {status && (
            <div className="small">
              <div>GTFS: {status.gtfs.loaded ? "loaded" : "error"} ({status.gtfs.stops} stops)</div>
              <div>Vehicles: {status.vehicles.age_seconds ?? "—"}s ago {status.vehicles.stale ? "(stale)" : ""}</div>
              <div>Trips: {status.trips.age_seconds ?? "—"}s ago {status.trips.stale ? "(stale)" : ""}</div>
              <div>Alerts: {status.alerts.age_seconds ?? "—"}s ago {status.alerts.stale ? "(stale)" : ""}</div>
            </div>
          )}
        </div>
      </aside>
      <main className="map-wrap">
        {network ? (
          <MapContainer center={AUCKLAND_CENTER} zoom={11} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              url="https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=cb1_4txz_1_78dd8ce046a1130aee6d93cf"
              attribution='&copy; OpenStreetMap &copy; CARTO'
            />
            {Array.from(shapesByRoute.entries()).map(([rid, shapeList]) =>
              shapeList.map((pts: [number, number][], i: number) => (
                <Polyline
                  key={`${rid}-${i}`}
                  positions={pts}
                  color={`#${routeMap.get(rid)?.color || "888888"}`}
                  weight={3}
                  opacity={0.8}
                />
              ))
            )}
            {stationMarkers.map((s) => (
              <CircleMarker
                key={s.stop_id}
                center={[s.lat, s.lon]}
                radius={4}
                color="#ffffff"
                weight={1}
                fillColor="#1f2937"
                fillOpacity={1}
                eventHandlers={{ click: () => setSelectedStop(s.stop_id) }}
              >
                <Popup>
                  <strong>{s.name}</strong>
                  {s.platform ? <div>Platform {s.platform}</div> : null}
                  <button onClick={() => setSelectedStop(s.stop_id)}>Arrivals</button>
                </Popup>
              </CircleMarker>
            ))}
            {filteredVehicles.map((v) => {
              const color = v.route_id ? `#${routeMap.get(v.route_id)?.color || "888888"}` : "#ffffff";
              const icon = L.divIcon({
                className: "",
                html: `<div style="width:14px;height:14px;background:${color};border:2px solid #fff;border-radius:50%;transform:rotate(${v.bearing ?? 0}deg);box-shadow:0 0 4px rgba(0,0,0,0.6);"></div>`,
                iconSize: [14, 14],
                iconAnchor: [7, 7],
              });
              return (
                <Marker key={v.id} position={[v.latitude, v.longitude]} icon={icon}>
                  <Popup>
                    <div><strong>{v.vehicle_label || v.vehicle_id}</strong></div>
                    <div>Route: {v.route_id || "—"}</div>
                    <div>Trip: {v.trip_id || "—"}</div>
                    {v.nextStopName && <div>Next: {v.nextStopName}</div>}
                    <div>Updated: {v.timestamp ? new Date(v.timestamp * 1000).toLocaleTimeString() : "—"}</div>
                    {v.bearing !== null && <div>Bearing: {Math.round(v.bearing)}°</div>}
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        ) : (
          <div className="spinner" style={{ padding: 20 }}>Loading network…</div>
        )}
        <div className="legend">
          {network?.routes.filter((r) => enabledRoutes.has(r.route_id)).map((r) => (
            <div key={r.route_id}>
              <span className="line-swatch" style={{ background: `#${r.color}`, width: 10, height: 10, display: "inline-block", borderRadius: 2 }} />
              {r.short_name}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
