class PCMRecorder extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const input = inputs[0];
    if (input?.[0]) {
      const mono = new Float32Array(input[0].length);
      for (const channel of input) for (let i=0;i<mono.length;i++) mono[i] += channel[i]/input.length;
      this.port.postMessage(mono, [mono.buffer]);
    }
    // Keep the graph alive while outputting silence (no microphone monitoring).
    outputs[0]?.forEach(channel=>channel.fill(0));
    return true;
  }
}
registerProcessor('pcm-recorder', PCMRecorder);
