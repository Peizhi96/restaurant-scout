"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createExternalLead, updateExternalLead } from "@/lib/api";

function optional(value: FormDataEntryValue | null): string | null {
  const result = String(value ?? "").trim();
  return result || null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The external lead could not be saved.";
}

export async function addExternalLead(formData: FormData) {
  let error: string | null = null;
  try {
    await createExternalLead({
      source_url: String(formData.get("source_url") ?? "").trim(),
      city: optional(formData.get("city")),
      notes: optional(formData.get("notes")),
    });
  } catch (caught) {
    error = errorMessage(caught);
  }
  if (error) redirect(`/external-leads?error=${encodeURIComponent(error)}`);
  revalidatePath("/external-leads");
  redirect("/external-leads?added=1");
}

export async function saveExternalLead(formData: FormData) {
  const id = String(formData.get("id") ?? "");
  let error: string | null = null;
  try {
    await updateExternalLead(id, {
      city: optional(formData.get("city")),
      status: String(formData.get("status") ?? "NEW"),
      notes: optional(formData.get("notes")),
    });
  } catch (caught) {
    error = errorMessage(caught);
  }
  if (error) redirect(`/external-leads?error=${encodeURIComponent(error)}`);
  revalidatePath("/external-leads");
  redirect("/external-leads?saved=1");
}
