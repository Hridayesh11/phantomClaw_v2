import axios from "axios";

// Read from NEXT_PUBLIC_API_URL or default to localhost:8000
const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  // In a real app we might add interceptors here for auth
});
