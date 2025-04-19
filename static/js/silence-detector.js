// silence-detector.js
class SilenceDetectorProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    
    // Configuration parameters
    this.silenceThreshold = 0.01; // Threshold for considering sound as silence
    this.smoothingFactor = 0.2; // For smoothing the volume calculation
    this.analysisWindowSize = 2048; // Number of samples to analyze at once
    this.silenceCounter = 0; // Count consecutive silence frames
    this.silenceFrameThreshold = 5; // Number of silent frames to trigger detection
    this.currentVolume = 0; // Smoothed volume level
    
    // Initialize buffer for analysis
    this.analysisBuffer = new Float32Array(this.analysisWindowSize);
    this.bufferFill = 0; // Current position in buffer
  }

  calculateRMS(inputs) {
    // Get the input channel data
    const inputChannel = inputs[0][0];
    if (!inputChannel) return 0;
    
    // Add current frame to analysis buffer
    for (let i = 0; i < inputChannel.length; i++) {
      if (this.bufferFill < this.analysisWindowSize) {
        this.analysisBuffer[this.bufferFill++] = inputChannel[i];
      }
    }
    
    // Only calculate RMS when we have enough data
    if (this.bufferFill < this.analysisWindowSize) return this.currentVolume;
    
    // Calculate RMS (Root Mean Square) of the buffer
    let sumSquares = 0;
    for (let i = 0; i < this.analysisWindowSize; i++) {
      sumSquares += this.analysisBuffer[i] * this.analysisBuffer[i];
    }
    
    // Calculate RMS and apply smoothing
    const rms = Math.sqrt(sumSquares / this.analysisWindowSize);
    this.currentVolume = this.currentVolume * (1 - this.smoothingFactor) + rms * this.smoothingFactor;
    
    // Reset buffer for next analysis
    this.bufferFill = 0;
    
    return this.currentVolume;
  }

  process(inputs, outputs, parameters) {
    // Skip processing if we don't have input data
    if (!inputs[0] || !inputs[0][0]) return true;
    
    // Calculate current volume level
    const volume = this.calculateRMS(inputs);
    
    // Determine if current frame is silent
    const isSilent = volume < this.silenceThreshold;
    
    // Count consecutive silent frames
    if (isSilent) {
      this.silenceCounter++;
    } else {
      this.silenceCounter = 0;
    }
    
    // Send message to main thread when silence is detected
    // Only send when state changes or periodically to reduce message traffic
    if ((this.silenceCounter === this.silenceFrameThreshold) || 
        (this.silenceCounter > this.silenceFrameThreshold && this.silenceCounter % 20 === 0)) {
      this.port.postMessage({
        isSilentDetected: true,
        currentVolume: volume,
        silenceDuration: this.silenceCounter / sampleRate * 128 // Approximate duration in seconds
      });
    } else if (this.silenceCounter === 0) {
      this.port.postMessage({
        isSilentDetected: false,
        currentVolume: volume
      });
    }
    
    // Always return true to keep the processor alive
    return true;
  }
}

registerProcessor('silence-detector', SilenceDetectorProcessor);