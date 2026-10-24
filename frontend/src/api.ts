const BASE = `${import.meta.env.VITE_API_BASE ?? ""}/api`;

export async function fetchStatic(): Promise<any> {
  const r = await fetch(`${BASE}/static`);
  if (!r.ok) throw new Error(`static ${r.status}`);
  return r.json();
}

export async function fetchVehicles(): Promise<any> {
  const r = await fetch(`${BASE}/vehicles`);
  if (!r.ok) throw new Error(`vehicles ${r.status}`);
  return r.json();
}

export async function fetchArrivals(stopId: string): Promise<any> {
  const r = await fetch(`${BASE}/arrivals/${encodeURIComponent(stopId)}`);
  if (!r.ok) throw new Error(`arrivals ${r.status}`);
  return r.json();
}

export async function fetchAlerts(): Promise<any> {
  const r = await fetch(`${BASE}/alerts`);
  if (!r.ok) throw new Error(`alerts ${r.status}`);
  return r.json();
}

export async function fetchStatus(): Promise<any> {
  const r = await fetch(`${BASE}/status`);
  if (!r.ok) throw new Error(`status ${r.status}`);
  return r.json();
}
