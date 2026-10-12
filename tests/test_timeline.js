const assert = require("node:assert/strict");
const test = require("node:test");

global.window = {};
require("../app/static/timeline.js");

function makeRange(value) {
  return { value: String(value), max: "", min: "", listeners: {}, addEventListener(name, callback) {
    this.listeners[name] = callback;
  } };
}

function setup() {
  const startRange = makeRange(0);
  const endRange = makeRange(3);
  const selectionText = { textContent: "" };
  const selectionFill = { style: {} };
  const midTime = { textContent: "" };
  const endTime = { textContent: "" };
  const timeline = window.ClipGifTimeline.createTimeline({
    startRange, endRange, selectionText, selectionFill, midTime, endTime,
  }, { currentTime: 0 });
  return { timeline, startRange, endRange, selectionText };
}

test("timeline keeps decimal seconds and caps a selection at 60 seconds", () => {
  const { timeline, startRange, endRange, selectionText } = setup();
  timeline.setDuration(90);
  endRange.value = "70";
  const capped = timeline.update("end");
  assert.equal(capped.start, 0);
  assert.equal(capped.end, 60);
  startRange.value = "12.5";
  const fractional = timeline.update("start");
  assert.equal(fractional.start, 12.5);
  assert.equal(fractional.end, 60);
  assert.equal(selectionText.textContent, "00:12.5 - 01:00.0");
});

test("timeline prevents a zero-length range", () => {
  const { timeline, startRange, endRange } = setup();
  timeline.setDuration(12.5);
  endRange.value = "4";
  timeline.update("end");
  startRange.value = "4";
  const selected = timeline.update("start");
  assert.ok(Math.abs((selected.end - selected.start) - 0.1) < 1e-9);
  assert.equal(Number(endRange.value) > Number(startRange.value), true);
});

test("timeline formats minute and fractional-second labels", () => {
  assert.equal(window.ClipGifTimeline.formatTime(72.5), "01:12.5");
  assert.equal(window.ClipGifTimeline.formatTime(59.99), "01:00.0");
});
