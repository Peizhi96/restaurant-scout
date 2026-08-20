"use server";

import { revalidatePath } from "next/cache";

import { requireAuthenticatedOperator } from "@/lib/auth";
import {
  createFinancialMetric,
  updateDueDiligenceProfile,
  updateFinancialMetric,
} from "@/lib/api";

function optionalText(formData: FormData, name: string): string | null {
  const value = String(formData.get(name) ?? "").trim();
  return value || null;
}

function optionalBoolean(formData: FormData, name: string): boolean | null {
  const value = String(formData.get(name) ?? "UNKNOWN");
  if (value === "YES") return true;
  if (value === "NO") return false;
  return null;
}

export async function saveDueDiligenceProfile(formData: FormData) {
  const operatorId = await requireAuthenticatedOperator();
  const id = String(formData.get("id"));
  await updateDueDiligenceProfile(
    id,
    {
      access_method: String(formData.get("access_method")),
      access_status: String(formData.get("access_status")),
      external_url: optionalText(formData, "external_url"),
      broker_contact_name: optionalText(formData, "broker_contact_name"),
      broker_contact_email: optionalText(formData, "broker_contact_email"),
      broker_contact_phone: optionalText(formData, "broker_contact_phone"),
      inventory_included: optionalBoolean(formData, "inventory_included"),
      ffe_included: optionalBoolean(formData, "ffe_included"),
      notes: optionalText(formData, "notes"),
    },
    operatorId,
  );
  revalidatePath(`/listings/${id}`);
  revalidatePath(`/listings/${id}/due-diligence`);
}

export async function addFinancialMetric(formData: FormData) {
  const operatorId = await requireAuthenticatedOperator();
  const id = String(formData.get("id"));
  await createFinancialMetric(
    id,
    {
      metric_type: String(formData.get("metric_type")),
      amount: String(formData.get("amount")),
      currency: String(formData.get("currency") ?? "USD"),
      period_start: optionalText(formData, "period_start"),
      period_end: optionalText(formData, "period_end"),
      source: String(formData.get("source") ?? "").trim(),
      source_reference: optionalText(formData, "source_reference"),
      verification_status: "UNVERIFIED",
      notes: optionalText(formData, "metric_notes"),
    },
    operatorId,
  );
  revalidatePath(`/listings/${id}/due-diligence`);
}

export async function verifyFinancialMetric(formData: FormData) {
  const operatorId = await requireAuthenticatedOperator();
  const id = String(formData.get("id"));
  const metricId = String(formData.get("metric_id"));
  await updateFinancialMetric(
    id,
    metricId,
    { verification_status: "VERIFIED" },
    operatorId,
  );
  revalidatePath(`/listings/${id}/due-diligence`);
}
