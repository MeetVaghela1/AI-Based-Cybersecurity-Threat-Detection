import React from "react";

/**
 * HelpTip — a small "?" (or "i") badge that reveals a plain-language hint on
 * hover or focus. Used next to labels, counters and chart titles so a
 * non-technical reader can get a one-line explanation of anything unfamiliar.
 */
export default function HelpTip({ text, glyph = "?" }) {
  return (
    <span className="help-tip-wrap">
      <button
        type="button"
        className="help-tip"
        aria-label="Help"
        tabIndex={0}
      >
        {glyph}
      </button>
      <span className="help-tip-bubble" role="tooltip">
        {text}
      </span>
    </span>
  );
}
