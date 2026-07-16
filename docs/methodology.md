# Methodology

## Prototype status

The current website contains synthetic season-level fixtures. They exist to validate the interface, normalization logic and disclosure design. They are not claims about the six players' true career totals.

## Production definitions

### Appearance

An appearance is an official senior match in which the player entered the field. An unused substitute does not count. Youth, reserve, testimonial and unofficial tour matches are excluded from the default universe.

### Common support

When several players are normalized by age, appearances or career season, the default chart stops at the greatest point observed for all selected players. This prevents a retirement total from being compared with an active or truncated career at a different exposure.

### Goals

Penalty-shootout kicks are not goals. Own goals are not credited to an attacker. Production goal records will follow an identified match/competition source and retain disputes.

### Assists

Assist definitions differ between providers and were not consistently recorded historically. Production records will store the provider's definition and field-level coverage. Rates will use covered games or minutes only. Unknown assists will display as unavailable rather than zero.

### Match win

The default product definition will count a shootout victory as a team win for the player's advancement experience, while retaining conventional win/draw/loss after regulation or extra time as a separate field.

### Tournament entered and won

An edition counts as entered when the player makes at least one on-field appearance. It counts as won when the player's registered team wins and the player has appeared in the edition. Squad-only and final-contributor variants will be stored separately.

## Planned statistical universes

- Official senior, combined.
- Official club only.
- Senior national team only.
- All documented senior, including identifiable friendlies.
- Domestic league, domestic cup, continental club, intercontinental club.
- World Cup finals, national-team continental finals and qualification as separate categories.

## Provenance standard

Every production aggregate must be reproducible from match-level appearances and tournament editions. Each record will retain source, access date, extraction method, match status, field coverage and discrepancy notes.

