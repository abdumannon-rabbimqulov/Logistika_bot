/**
 * Backend / Postman bilan bir xil: telefon + belgisiz (masalan 998991134543).
 */
export function formatPhoneForApi(phone: string): string {
  let value = phone.trim().replace(/\s+/g, "").replace(/-/g, "");
  if (value && !value.startsWith("+") && value.length > 9) {
    value = "+" + value;
  }
  return value;
}
