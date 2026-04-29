export type ApiError = {
  message: string;
  detail?: string[];
  statusCode?: number;
};

export type HealthResponse = {
  status: string;
  timestamp?: string;
  models: {
    crop: string;
    fertilizer: string;
    disease: string;
  };
  llm: {
    provider: string;
    model: string;
  };
};

export type CropRequest = {
  N: number;
  P: number;
  K: number;
  ph: number;
  temperature?: number;
  humidity?: number;
  rainfall?: number;
  month?: number;
  top_n?: number;
  location?: string;
};

export type CropRecommendation = {
  crop: string;
  composite_score: number;
  ml_probability: number;
  seasonal_score: number;
  weather_score: number;
};

export type CropResponse = {
  success: boolean;
  tool: string;
  explanation: string;
  next_action: string;
  primary_crop?: string;
  season?: string;
  confidence?: string;
  seasonal_score?: number;
  weather_score?: number;
  why_this_crop_now?: string;
  uncertainty_score?: number;
  top_recommendations?: CropRecommendation[];
};

export type FertilizerRequest = {
  temperature: number;
  humidity: number;
  moisture: number;
  nitrogen: number;
  phosphorous: number;
  potassium: number;
  soil_type: string;
  crop_type: string;
};

export type FertilizerRecommendation = {
  fertilizer: string;
  probability: number;
};

export type FertilizerResponse = {
  success: boolean;
  tool: string;
  explanation: string;
  next_action: string;
  primary_fertilizer?: string;
  confidence?: number;
  rule_applied?: boolean;
  rule_reason?: string;
  top_recommendations?: FertilizerRecommendation[];
};

export type DiseaseTopPrediction = {
  disease: string;
  confidence: number;
};

export type DiseaseResponse = {
  success: boolean;
  tool: string;
  explanation: string;
  next_action: string;
  primary_disease?: string;
  crop?: string;
  confidence?: number;
  is_healthy?: boolean;
  severity?: string;
  treatment_recommendations?: string[];
  top_3?: DiseaseTopPrediction[];
};

export type ChatRequest = {
  query: string;
  session_id: string;
};

export type ChatResponse = {
  success: boolean;
  session_id?: string;
  intent?: string;
  tool_used?: string;
  explanation: string;
  next_action?: string;
  llm_mode?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "ai";
  content: string;
  timestamp: number;
  pending?: boolean;
  error?: boolean;
};
