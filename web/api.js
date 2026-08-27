// Frontend API contract for the next backend phase.
// The current static MVP remains runnable without a backend.

export const API_ROUTES = {
  chat: '/api/chat',
  analyze: '/api/analyze',
  upload: '/api/upload',
  leads: '/api/leads',
  adminSummary: '/api/admin/summary',
  adminLeads: '/api/admin/leads'
};

export const LEAD_STATUS = ['NEW', 'QUALIFIED', 'CONTACTED', 'CONVERTED', 'LOST'];

export function buildChatPayload({ message, imageId, profile, source = 'web' }) {
  return { message, image_id: imageId || null, profile, source };
}
