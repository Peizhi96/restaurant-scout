"use server";

import { revalidatePath } from "next/cache";

import { updateListing } from "@/lib/api";

export async function saveListing(formData: FormData) {
  const id = String(formData.get("id"));
  const status = String(formData.get("status"));
  const notes = String(formData.get("notes") ?? "");
  await updateListing(id, { status, notes: notes || null });
  revalidatePath(`/listings/${id}`);
  revalidatePath("/dashboard");
  revalidatePath("/listings");
}
