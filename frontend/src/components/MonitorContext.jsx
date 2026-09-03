// MonitorContext.jsx — owns the "live" monitoring loop so it keeps running no
// matter which tab you are on.  The Dashboard reads this to render the packet
// stream; the Compare page and the Database tab read the same server-side log
// (GET /predictions) for live latency stats and stored records.
import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const MonitorContext = createContext(null);
export const useMonitor = () => useContext(MonitorContext);

const MAX_PACKETS = 28;
const BATCH_SIZE = 15;

export function MonitorProvider({ children }) {
  const [dataset, setDataset] = useState("nslkdd");
  const [model, setModel] = useState("xgboost");
  const [running, setRunning] = useState(false);
  const [packets, setPackets] = useState([]);
  const [error, setError] = useState(null);
  const [log, setLog] = useState({ count: 0, items: [] });

  const timer = useRef(null);
  const logTimer = useRef(null);
  const seq = useRef(0);

  const fetchBatch = async () => {
    try {
      const body = await api.simulate(dataset, model, BATCH_SIZE);
      const now = new Date();
      const stamped = body.items.map((it) => ({
        ...it,
        seq: seq.current++,
        time: now.toLocaleTimeString([], { hour12: false }),
      }));
      setPackets((prev) => [...stamped, ...prev].slice(0, MAX_PACKETS));
      setError(null);
    } catch (e) {
      setError(`Cannot reach the backend: ${e.message}. Is uvicorn running on :8000?`);
    }
  };

  const refreshLog = async () => {
    try {
      setLog(await api.predictions());
    } catch {
      /* backend not reachable — keep the last log */
    }
  };

  const start = () => {
    setRunning(true);
    setPackets([]);
    fetchBatch();
    timer.current = setInterval(fetchBatch, 1600);
  };

  const stop = () => {
    setRunning(false);
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  };

  // Show whatever is already stored as soon as the app loads.
  useEffect(() => {
    refreshLog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the log fresh (live latency + Database tab) while the stream runs.
  useEffect(() => {
    if (!running) return;
    refreshLog();
    logTimer.current = setInterval(refreshLog, 2000);
    return () => {
      if (logTimer.current) clearInterval(logTimer.current);
      logTimer.current = null;
    };
  }, [running]);

  // Switching dataset/model mid-run restarts the stream with the new choice.
  useEffect(() => {
    if (running) {
      setPackets([]);
      if (timer.current) clearInterval(timer.current);
      fetchBatch();
      timer.current = setInterval(fetchBatch, 1600);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset, model]);

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
      if (logTimer.current) clearInterval(logTimer.current);
    },
    []
  );

  const value = {
    dataset,
    setDataset,
    model,
    setModel,
    running,
    start,
    stop,
    packets,
    error,
    log,
  };

  return (
    <MonitorContext.Provider value={value}>{children}</MonitorContext.Provider>
  );
}
