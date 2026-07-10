import { createContext, useContext } from "react";
import type { FeatureConfig } from "./api";

export const defaultFeatures: FeatureConfig["features"] = {
  chat: true,
  document_upload: true,
  audio_upload: true,
  youtube: true,
  web_scraping: true,
  podcast_script: true,
  podcast_audio: true,
  memory: true,
};

export const FeaturesContext = createContext<FeatureConfig["features"]>(defaultFeatures);

export function useFeatures() {
  return useContext(FeaturesContext);
}