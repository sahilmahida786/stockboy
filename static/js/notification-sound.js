/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — NOTIFICATION SOUND ENGINE
 *  Handles lightweight notification audio
 * ════════════════════════════════════════════════════════════════
 */

window.StockboySound = (function() {
  'use strict';

  // Default to muted based on user preference or local storage
  let isMuted = localStorage.getItem('sb_notif_muted') !== 'false';
  let audioContext = null;

  function initAudioContext() {
    if (!audioContext) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioContext = new AudioContext();
      }
    }
  }

  // Generate a premium "ding" using Web Audio API instead of loading a heavy MP3
  function playDing() {
    if (isMuted) return;
    try {
      initAudioContext();
      if (!audioContext) return;

      // Resume context if suspended (browser auto-play policy)
      if (audioContext.state === 'suspended') {
        audioContext.resume();
      }

      const osc = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioContext.currentTime); // A5
      osc.frequency.exponentialRampToValueAtTime(1760, audioContext.currentTime + 0.1); // A6

      gainNode.gain.setValueAtTime(0, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.05);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.5);

      osc.connect(gainNode);
      gainNode.connect(audioContext.destination);

      osc.start();
      osc.stop(audioContext.currentTime + 0.5);
    } catch (e) {
      console.warn("Audio playback failed", e);
    }
  }

  function toggleMute() {
    isMuted = !isMuted;
    localStorage.setItem('sb_notif_muted', isMuted);
    
    // Auto-init audio context on user interaction if unmuted
    if (!isMuted) {
      initAudioContext();
      if (audioContext && audioContext.state === 'suspended') {
        audioContext.resume();
      }
      playDing(); // Play a test sound to confirm unmuted
    }
    
    return isMuted;
  }

  function getIsMuted() {
    return isMuted;
  }

  return {
    playNotification: playDing,
    toggleMute,
    getIsMuted
  };

})();
