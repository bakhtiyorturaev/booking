# Auth method selector design QA

- Source visual truth: user-provided conversation screenshot (Google, Apple, and phone pill controls; Apple explicitly excluded).
- Source pixels: 445 × 312 px.
- Implementation: `http://localhost:3000/login`, initial guest state, dark theme.
- Implementation screenshot: unavailable because no controllable browser is available in this session.
- Intended viewport: desktop auth panel, 390 CSS px component width, device scale factor 1.
- Density normalization: not performed; implementation capture is unavailable.

**Findings**

- [Blocked] A browser-rendered implementation screenshot could not be captured, so fonts, exact spacing, colors, Google-rendered iframe dimensions, and responsive behavior cannot be compared visually against the source.
- Code-level correspondence: two pill controls only; Google uses the official GIS-rendered button with `continue_with` and `pill`; phone uses the existing Font Awesome phone icon; Apple is absent.

**Full-view comparison evidence**

- Source screenshot is available in the conversation.
- No browser-rendered implementation capture is available, so a normalized side-by-side comparison cannot be produced.

**Focused region comparison evidence**

- Not available for the same browser-capture blocker.

**Comparison history**

- Initial implementation created the two-method selector and deferred the phone form until selection.
- No visual iteration could be performed without an implementation screenshot.

**Implementation checklist**

- Capture `/login` and `/register` in dark and light themes.
- Verify the official Google iframe fills the 390 px control width.
- Verify the phone control matches Google control height, radius, border, and typography.
- Test phone selection and return interaction on desktop and mobile.

final result: blocked
