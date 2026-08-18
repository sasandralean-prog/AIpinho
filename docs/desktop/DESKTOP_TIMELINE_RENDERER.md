# Desktop Timeline Renderer

Chat terminals use selectable `tk.Text` widgets with dedicated scrollbars.

Rendering rules:

- chronological order;
- latest message at the bottom;
- initial load scrolls to the bottom;
- refresh scrolls only when the user was already at the bottom;
- normal mode shows human conversation;
- details mode adds sanitized events;
- raw mode is explicit and sanitized.

Scrollable side panels only respond when the pointer is inside that panel,
preventing one wheel action from moving unrelated cards.

