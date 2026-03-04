/**
 * AudioWorklet processor for microphone capture.
 *
 * Collects PCM float32 frames from the mic, converts to PCM16 (Int16),
 * and posts them to the main thread for sending to Voice Live API.
 *
 * Expected AudioContext sample rate: 24 000 Hz (set when creating the context).
 */
class MicProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // ~100 ms of audio at 24 kHz
    this.bufferSize = 2400;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // mono

    for (let i = 0; i < channelData.length; i++) {
      this.buffer[this.bufferIndex++] = channelData[i];

      if (this.bufferIndex >= this.bufferSize) {
        // Convert float32 → int16 PCM
        const pcm16 = new Int16Array(this.bufferSize);
        for (let j = 0; j < this.bufferSize; j++) {
          const s = Math.max(-1, Math.min(1, this.buffer[j]));
          pcm16[j] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);

        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
      }
    }

    return true;
  }
}

registerProcessor("mic-processor", MicProcessor);
