import React from "react";

/** A small coloured pill used to mark traffic as normal / attack / info. */
export default function StatusPill({ kind, children }) {
  return <span className={`pill ${kind}`}>{children}</span>;
}
