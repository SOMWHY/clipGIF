const assert = require("node:assert/strict");
const test = require("node:test");

global.window = {};
require("../app/static/crop.js");

function makeElement(bounds = { left: 10, top: 20, width: 200, height: 100 }) {
  return {
    bounds,
    hidden: false,
    textContent: "",
    style: {},
    attributes: {},
    listeners: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    getBoundingClientRect() {
      return this.bounds;
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    dispatch(name, event = {}) {
      this.listeners[name]?.(event);
    },
  };
}

test("crop rect stays inside the frame when moved", () => {
  const frame = { left: 10, top: 20, width: 200, height: 100 };
  assert.deepEqual(
    window.ClipGifCrop.moveRect({ left: 150, top: 70, width: 50, height: 20 }, 40, 40, frame),
    { left: 160, top: 100, width: 50, height: 20 },
  );
});

test("crop region is normalized to displayed video bounds", () => {
  assert.deepEqual(
    window.ClipGifCrop.normalizeRect(
      { left: 60, top: 45, width: 100, height: 50 },
      { left: 10, top: 20, width: 200, height: 100 },
    ),
    { x: 0.25, y: 0.25, width: 0.5, height: 0.5 },
  );
});

test("crop resize remains inside bounds and honors the minimum size", () => {
  const bounds = { left: 0, top: 0, width: 200, height: 100 };
  const initial = { left: 60, top: 20, width: 80, height: 40 };
  assert.deepEqual(
    window.ClipGifCrop.resizeRect(initial, "se", 200, 200, bounds, 20, 20),
    { left: 60, top: 20, width: 140, height: 80 },
  );
  assert.deepEqual(
    window.ClipGifCrop.resizeRect(initial, "nw", 200, 200, bounds, 20, 20),
    { left: 120, top: 40, width: 20, height: 20 },
  );
  assert.deepEqual(
    window.ClipGifCrop.resizeRect(initial, "ne", 200, 200, bounds, 20, 20),
    { left: 60, top: 40, width: 140, height: 20 },
  );
  assert.deepEqual(
    window.ClipGifCrop.resizeRect(initial, "sw", -200, -200, bounds, 20, 20),
    { left: 0, top: 20, width: 140, height: 20 },
  );
});

test("crop controller enables, resets, and disables a full-frame crop", () => {
  const overlay = makeElement();
  overlay.hidden = true;
  const box = makeElement();
  box.querySelectorAll = () => [];
  overlay.querySelector = () => box;
  const frame = makeElement();
  frame.querySelector = (selector) => selector === "[data-crop-overlay]" ? overlay : null;
  const video = makeElement();
  video.videoWidth = 640;
  video.videoHeight = 360;
  video.addEventListener = () => {};
  const toggle = makeElement();
  const reset = makeElement();
  const crop = window.ClipGifCrop.createCropOverlay({ frame, video, toggle, reset });

  assert.equal(crop.region(), null);
  toggle.dispatch("click");
  assert.deepEqual(crop.region(), { x: 0, y: 0, width: 1, height: 1 });
  reset.dispatch("click");
  assert.deepEqual(crop.region(), { x: 0, y: 0, width: 1, height: 1 });
  toggle.dispatch("click");
  assert.equal(crop.region(), null);
});
