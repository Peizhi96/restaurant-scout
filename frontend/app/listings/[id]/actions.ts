"use server";

import { revalidatePath } from "next/cache";

import { generateAIAnalysis, updateListing } from "@/lib/api";
import { requireAuthenticatedOperator } from "@/lib/auth";

export async function saveListing(formData: FormData) {
  await requireAuthenticatedOperator();
  const id = String(formData.get("id"));
  const status = String(formData.get("status"));
  const notes = String(formData.get("notes") ?? "");
  await updateListing(id, { status, notes: notes || null });
  revalidatePath(`/listings/${id}`);
  revalidatePath("/dashboard");
  revalidatePath("/listings");
}

export async function refreshAIAnalysis(formData: FormData) {
  await requireAuthenticatedOperator();
  const id = String(formData.get("id"));
  await generateAIAnalysis(id);
  revalidatePath(`/listings/${id}`);
}
