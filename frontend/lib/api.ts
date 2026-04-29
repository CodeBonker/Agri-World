import axios, { AxiosError } from "axios";
import { API_BASE_URL } from "@/lib/constants";
import type {
  ApiError,
  ChatRequest,
  ChatResponse,
  CropRequest,
  CropResponse,
  DiseaseResponse,
  FertilizerRequest,
  FertilizerResponse,
  HealthResponse,
} from "@/lib/types";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

function parseError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<{ detail?: string[] | string; error?: string }>;
    const detail = err.response?.data?.detail;
    return {
      message:
        err.response?.data?.error ||
        (Array.isArray(detail) ? detail.join(" | ") : detail) ||
        err.message ||
        "Request failed",
      detail: Array.isArray(detail) ? detail : detail ? [detail] : undefined,
      statusCode: err.response?.status,
    };
  }
  return { message: "Unexpected error" };
}

export async function getHealth() {
  try {
    const { data } = await client.get<HealthResponse>("/health");
    return data;
  } catch (error) {
    throw parseError(error);
  }
}

export async function postCrop(payload: CropRequest) {
  try {
    const { data } = await client.post<CropResponse>("/api/crop", payload);
    return data;
  } catch (error) {
    throw parseError(error);
  }
}

export async function postFertilizer(payload: FertilizerRequest) {
  try {
    const { data } = await client.post<FertilizerResponse>("/api/fertilizer", payload);
    return data;
  } catch (error) {
    throw parseError(error);
  }
}

export async function postDisease(file: File) {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await client.post<DiseaseResponse>("/api/disease", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  } catch (error) {
    throw parseError(error);
  }
}

export async function postChat(payload: ChatRequest) {
  try {
    const { data } = await client.post<ChatResponse>("/api/chat", payload);
    return data;
  } catch (error) {
    throw parseError(error);
  }
}

export async function clearChatSession(sessionId: string) {
  try {
    await client.delete(`/api/chat/session/${sessionId}`);
  } catch (error) {
    throw parseError(error);
  }
}
