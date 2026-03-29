/**
 * voice.js — Web Speech API wrapper for voice input
 */

const Voice = (() => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let _onResult = null;
  let _onEnd    = null;
  let _active   = false;

  const isSupported = !!SpeechRecognition;

  function init() {
    if (!isSupported) return;
    recognition = new SpeechRecognition();
    recognition.continuous      = false;
    recognition.interimResults  = true;
    recognition.lang            = "en-US";
    recognition.maxAlternatives = 1;

    recognition.onresult = (e) => {
      let transcript = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
      }
      const isFinal = e.results[e.results.length - 1].isFinal;
      if (_onResult) _onResult(transcript, isFinal);
    };

    recognition.onend  = () => { _active = false; if (_onEnd) _onEnd(); };
    recognition.onerror = (e) => {
      _active = false;
      console.warn("Speech error:", e.error);
      if (_onEnd) _onEnd(e.error);
    };
  }

  function start(onResult, onEnd) {
    if (!isSupported || _active) return false;
    _onResult = onResult;
    _onEnd    = onEnd;
    _active   = true;
    recognition.start();
    return true;
  }

  function stop() {
    if (recognition && _active) recognition.stop();
  }

  init();
  return { isSupported, start, stop, get active() { return _active; } };
})();
