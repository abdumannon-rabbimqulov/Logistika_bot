/**
 * Backend / Postman bilan bir xil: telefon + belgisiz (masalan 998991134543).
 */
export function formatPhoneForApi(phone: string): string {
  return phone.trim().replace(/[\s-]/g, "");
}
