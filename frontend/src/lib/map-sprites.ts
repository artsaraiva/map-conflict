/**
 * Map sprite/icon generation utilities.
 * Creates canvas-based icons for vehicles and event-type markers
 * that can be loaded into MapLibre via addImage().
 *
 * All event-type icons are rendered at 48px for HiDPI clarity
 * and loaded with pixelRatio: 2 for crisp display.
 */

import { EVENT_TYPE_CONFIG } from "@/lib/types";

/** Create a top-down plane silhouette (pointing UP = 0 degrees) */
export function createPlaneSprite(size = 28, color = "#d4c8a8"): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  const cx = size / 2;
  const cy = size / 2;
  const s = size / 28; // scale factor

  ctx.fillStyle = color;
  ctx.strokeStyle = "rgba(0,0,0,0.3)";
  ctx.lineWidth = 0.5 * s;

  // Fuselage (vertical, pointing up)
  ctx.beginPath();
  ctx.moveTo(cx, cy - 12 * s); // nose
  ctx.lineTo(cx - 1.5 * s, cy - 6 * s);
  ctx.lineTo(cx - 1.5 * s, cy + 10 * s);
  ctx.lineTo(cx, cy + 12 * s); // tail
  ctx.lineTo(cx + 1.5 * s, cy + 10 * s);
  ctx.lineTo(cx + 1.5 * s, cy - 6 * s);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Main wings
  ctx.beginPath();
  ctx.moveTo(cx - 1.5 * s, cy - 1 * s);
  ctx.lineTo(cx - 11 * s, cy + 3 * s);
  ctx.lineTo(cx - 10 * s, cy + 5 * s);
  ctx.lineTo(cx - 1.5 * s, cy + 2 * s);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(cx + 1.5 * s, cy - 1 * s);
  ctx.lineTo(cx + 11 * s, cy + 3 * s);
  ctx.lineTo(cx + 10 * s, cy + 5 * s);
  ctx.lineTo(cx + 1.5 * s, cy + 2 * s);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Tail fins
  ctx.beginPath();
  ctx.moveTo(cx - 1.5 * s, cy + 8 * s);
  ctx.lineTo(cx - 5 * s, cy + 11 * s);
  ctx.lineTo(cx - 4 * s, cy + 12 * s);
  ctx.lineTo(cx - 1.5 * s, cy + 10 * s);
  ctx.closePath();
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(cx + 1.5 * s, cy + 8 * s);
  ctx.lineTo(cx + 5 * s, cy + 11 * s);
  ctx.lineTo(cx + 4 * s, cy + 12 * s);
  ctx.lineTo(cx + 1.5 * s, cy + 10 * s);
  ctx.closePath();
  ctx.fill();

  return ctx.getImageData(0, 0, size, size);
}

/** Create a top-down ship/boat silhouette (pointing UP = 0 degrees) */
export function createBoatSprite(size = 24, color = "#a8b8c4"): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  const cx = size / 2;
  const cy = size / 2;
  const s = size / 24;

  ctx.fillStyle = color;
  ctx.strokeStyle = "rgba(0,0,0,0.3)";
  ctx.lineWidth = 0.5 * s;

  // Hull (pointed bow at top)
  ctx.beginPath();
  ctx.moveTo(cx, cy - 10 * s); // bow
  ctx.lineTo(cx - 4 * s, cy - 3 * s);
  ctx.lineTo(cx - 4 * s, cy + 8 * s);
  ctx.lineTo(cx - 2 * s, cy + 10 * s); // stern left
  ctx.lineTo(cx + 2 * s, cy + 10 * s); // stern right
  ctx.lineTo(cx + 4 * s, cy + 8 * s);
  ctx.lineTo(cx + 4 * s, cy - 3 * s);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Superstructure / bridge
  ctx.fillStyle = shiftColor(color, -20);
  ctx.fillRect(cx - 2.5 * s, cy - 2 * s, 5 * s, 6 * s);

  // Deck line
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.lineWidth = 0.8 * s;
  ctx.beginPath();
  ctx.moveTo(cx - 3 * s, cy - 1 * s);
  ctx.lineTo(cx + 3 * s, cy - 1 * s);
  ctx.stroke();

  return ctx.getImageData(0, 0, size, size);
}

function shiftColor(hex: string, amount: number): string {
  const r = Math.max(
    0,
    Math.min(255, parseInt(hex.slice(1, 3), 16) + amount)
  );
  const g = Math.max(
    0,
    Math.min(255, parseInt(hex.slice(3, 5), 16) + amount)
  );
  const b = Math.max(
    0,
    Math.min(255, parseInt(hex.slice(5, 7), 16) + amount)
  );
  return `rgb(${r},${g},${b})`;
}

// ─── Event Type Icon Sprites ───

/**
 * Generate all event-type icon sprites for use as MapLibre symbol images.
 * Each icon is rendered at 48px on a dark circle background with a colored
 * border and symbol. Designed for pixelRatio: 2 (24px effective display).
 * Returns a map of icon name -> ImageData.
 */
export function createEventTypeIcons(
  size = 48
): Map<string, ImageData> {
  const icons = new Map<string, ImageData>();

  for (const [eventType, config] of Object.entries(EVENT_TYPE_CONFIG)) {
    const iconName = `event-icon-${eventType}`;
    const iconData = drawEventIcon(size, config.color, config.icon);
    icons.set(iconName, iconData);
  }

  return icons;
}

/** Draw a single event-type icon on a dark circular background */
function drawEventIcon(
  size: number,
  color: string,
  iconType: string
): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 1.5;

  // Dark circle background with colored border
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(10, 16, 22, 0.92)";
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();

  // Draw icon shape in the center
  ctx.fillStyle = color;
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;

  const s = size / 48; // scale relative to 48px base

  switch (iconType) {
    case "crossed-swords": // conflict — explosion/burst star
      drawExplosionBurst(ctx, cx, cy, s);
      break;
    case "anchor": // naval — anchor
      drawAnchor(ctx, cx, cy, s);
      break;
    case "handshake": // diplomatic — two opposing arrows
      drawDiplomaticArrows(ctx, cx, cy, s);
      break;
    case "ban": // sanctions — circle with slash
      drawBan(ctx, cx, cy, s);
      break;
    case "megaphone": // internal unrest — raised fist
      drawRaisedFist(ctx, cx, cy, s);
      break;
    case "tank": // military movement — double chevron
      drawDoubleChevron(ctx, cx, cy, s);
      break;
    case "chart": // trade dispute — dollar sign
      drawDollarSign(ctx, cx, cy, s);
      break;
    case "heart": // humanitarian — dove/pigeon
      drawDove(ctx, cx, cy, s, color);
      break;
    case "info": // other — info "i"
      drawInfo(ctx, cx, cy, s);
      break;
    default:
      drawInfo(ctx, cx, cy, s);
  }

  return ctx.getImageData(0, 0, size, size);
}

// ─── Icon drawing functions (scaled for 48px base) ───

function drawExplosionBurst(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // 6-pointed star/burst
  const spikes = 6;
  const outerR = 12 * s;
  const innerR = 6 * s;
  ctx.beginPath();
  for (let i = 0; i < spikes * 2; i++) {
    const angle = (i * Math.PI) / spikes - Math.PI / 2;
    const r = i % 2 === 0 ? outerR : innerR;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();
}

function drawAnchor(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  ctx.lineWidth = 2.2 * s;
  // Vertical line
  ctx.beginPath();
  ctx.moveTo(cx, cy - 9 * s);
  ctx.lineTo(cx, cy + 11 * s);
  ctx.stroke();
  // Top ring
  ctx.beginPath();
  ctx.arc(cx, cy - 11 * s, 2.5 * s, 0, Math.PI * 2);
  ctx.stroke();
  // Bottom curve
  ctx.beginPath();
  ctx.arc(cx, cy + 3 * s, 8 * s, 0, Math.PI);
  ctx.stroke();
  // Crossbar
  ctx.beginPath();
  ctx.moveTo(cx - 7 * s, cy - 4 * s);
  ctx.lineTo(cx + 7 * s, cy - 4 * s);
  ctx.stroke();
}

function drawDiplomaticArrows(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // Two opposing arrows pointing inward
  ctx.lineWidth = 2.2 * s;
  // Left arrow
  ctx.beginPath();
  ctx.moveTo(cx - 13 * s, cy);
  ctx.lineTo(cx - 3 * s, cy);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx - 7 * s, cy - 4 * s);
  ctx.lineTo(cx - 3 * s, cy);
  ctx.lineTo(cx - 7 * s, cy + 4 * s);
  ctx.stroke();
  // Right arrow
  ctx.beginPath();
  ctx.moveTo(cx + 13 * s, cy);
  ctx.lineTo(cx + 3 * s, cy);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 7 * s, cy - 4 * s);
  ctx.lineTo(cx + 3 * s, cy);
  ctx.lineTo(cx + 7 * s, cy + 4 * s);
  ctx.stroke();
}

function drawBan(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // Circle with diagonal slash
  ctx.lineWidth = 2.2 * s;
  ctx.beginPath();
  ctx.arc(cx, cy, 10 * s, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx - 7 * s, cy - 7 * s);
  ctx.lineTo(cx + 7 * s, cy + 7 * s);
  ctx.stroke();
}

function drawRaisedFist(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // Raised fist silhouette
  ctx.lineWidth = 1.5 * s;
  // Fist body
  ctx.beginPath();
  ctx.roundRect(cx - 6 * s, cy - 5 * s, 12 * s, 11 * s, 3 * s);
  ctx.fill();
  // Wrist
  ctx.fillRect(cx - 4.5 * s, cy + 6 * s, 9 * s, 6 * s);
  // Finger lines (etched into the fist)
  ctx.strokeStyle = "rgba(10, 16, 22, 0.55)";
  ctx.lineWidth = 1 * s;
  ctx.beginPath();
  ctx.moveTo(cx - 3 * s, cy - 5 * s);
  ctx.lineTo(cx - 3 * s, cy + 1 * s);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 0.5 * s, cy - 5 * s);
  ctx.lineTo(cx + 0.5 * s, cy + 1 * s);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 4 * s, cy - 5 * s);
  ctx.lineTo(cx + 4 * s, cy + 1 * s);
  ctx.stroke();
}

function drawDoubleChevron(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // Upward pointing double chevron — military movement
  ctx.lineWidth = 2.8 * s;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  // Upper chevron
  ctx.beginPath();
  ctx.moveTo(cx - 10 * s, cy + 2 * s);
  ctx.lineTo(cx, cy - 8 * s);
  ctx.lineTo(cx + 10 * s, cy + 2 * s);
  ctx.stroke();
  // Lower chevron
  ctx.beginPath();
  ctx.moveTo(cx - 7 * s, cy + 10 * s);
  ctx.lineTo(cx, cy + 2 * s);
  ctx.lineTo(cx + 7 * s, cy + 10 * s);
  ctx.stroke();
  ctx.lineCap = "butt";
  ctx.lineJoin = "miter";
}

function drawDollarSign(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // Dollar sign — trade/economic
  ctx.font = `bold ${20 * s}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("$", cx, cy + 1 * s);
}

function drawDove(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number,
  color: string
) {
  // Peace dove / pigeon silhouette facing right
  ctx.fillStyle = color;

  // Body — elongated ellipse, slightly angled
  ctx.save();
  ctx.translate(cx - 1 * s, cy + 2 * s);
  ctx.rotate(-0.15); // slight upward tilt
  ctx.beginPath();
  ctx.ellipse(0, 0, 9 * s, 5 * s, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // Head — circle at front-right of body
  ctx.beginPath();
  ctx.arc(cx + 7 * s, cy - 1 * s, 4 * s, 0, Math.PI * 2);
  ctx.fill();

  // Beak — small triangle
  ctx.beginPath();
  ctx.moveTo(cx + 11 * s, cy - 1.5 * s);
  ctx.lineTo(cx + 14 * s, cy - 0.5 * s);
  ctx.lineTo(cx + 11 * s, cy + 0.5 * s);
  ctx.closePath();
  ctx.fill();

  // Wing — swept upward arc from body
  ctx.beginPath();
  ctx.moveTo(cx - 4 * s, cy + 0 * s); // wing root (back of body)
  ctx.quadraticCurveTo(cx - 6 * s, cy - 10 * s, cx + 4 * s, cy - 11 * s); // top of wing sweep
  ctx.quadraticCurveTo(cx + 6 * s, cy - 7 * s, cx + 3 * s, cy - 2 * s); // back down to body
  ctx.closePath();
  ctx.fill();

  // Tail — fan shape at the back
  ctx.beginPath();
  ctx.moveTo(cx - 8 * s, cy + 0 * s); // tail root
  ctx.lineTo(cx - 14 * s, cy - 3 * s); // upper tail
  ctx.lineTo(cx - 13 * s, cy + 1 * s); // mid tail
  ctx.lineTo(cx - 14 * s, cy + 5 * s); // lower tail
  ctx.lineTo(cx - 8 * s, cy + 4 * s); // back to body
  ctx.closePath();
  ctx.fill();

  // Eye — small dark dot
  ctx.fillStyle = "rgba(10, 16, 22, 0.7)";
  ctx.beginPath();
  ctx.arc(cx + 8 * s, cy - 2 * s, 1 * s, 0, Math.PI * 2);
  ctx.fill();
}

function drawInfo(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  s: number
) {
  // Info "i" — generic
  ctx.font = `bold ${20 * s}px serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("i", cx, cy + 1 * s);
}
