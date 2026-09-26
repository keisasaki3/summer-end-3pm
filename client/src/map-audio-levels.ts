export type AudioMapId = "yunagicho" | "komorebi" | "convenience";

// Per-map perceptual loudness compensation.
// Final playback volume = user master volume * map gain.
// Keep these values with the map/audio configuration so new maps can be
// calibrated once without changing the user's master-volume behavior.
export const MAP_AUDIO_GAIN: Record<AudioMapId, number> = {
  yunagicho: 1.0,
  komorebi: 0.25,
  convenience: 1.0,
};

const AUDIO_KEY_TO_MAP: Record<string, AudioMapId> = {
  "yunagicho-perves-village": "yunagicho",
  "komorebi-cicadas-birds": "komorebi",
  "convenience-night-ambience": "convenience",
};

export const isMapAudioKey = (audioKey: string): boolean =>
  Object.prototype.hasOwnProperty.call(AUDIO_KEY_TO_MAP, audioKey);

export const getMapAudioGainForKey = (audioKey: string): number => {
  const mapId = AUDIO_KEY_TO_MAP[audioKey];
  return mapId ? MAP_AUDIO_GAIN[mapId] : 1.0;
};
