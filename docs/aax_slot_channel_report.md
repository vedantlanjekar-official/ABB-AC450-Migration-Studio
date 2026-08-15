# AAX Slot/Card and Channel Extraction — Technical Report

**Scope:** `backend/pc_element/parser/aax_reader.py` only (Stages 4F and 4G).  
**Corpus:** 32 AAX files in `.AXX Data/` (PM2 `23JA*` and PM3 `N22*` twins).  
**Unchanged:** device-tag / loop-tag extraction rules, category mapping, clubbing, Function Block Summary, Excel layout, output formatting.

---

## 1. Root cause

PC Element AAX files are **function-block diagrams**, not DB I/O lists. They do **not** store `:ADDR` card numbers the way BAX/PDF DB listings do.

The previous reader did two things that left Slot/Card and Channel empty (Excel `0` / blank):

1. **Soft fallback.** Any plant tag without a local `=AIcard.channel` string was emitted as `=CAT0.0/DeviceTag`. GrammarParser then stored `card_number=0`, `channel_number=0`.
2. **PCU addressing was ignored.** Pulse-counter blocks (`PCU-I` / `PCU-O`) carry the real module/channel as `:IOADDR` + `:CHANNEL` (e.g. 192 / 1). The reader synthesised `.SPEEDMV` / `.PULSEOUT` tags but still wrote `AI0.0` / `DO0.0`.
3. **Same-block join was incomplete.** A MOVE such as `:21 =82PIC972:POUT` + `:22 =AO3.9` produced `AO3.9/82PIC972.OUT` from the page title, but left `AO0.0/82PIC972.POUT` unaddressed. Named FB params (`:MV`, `:MC`, `:SO1`, `:CLS`) could lose to a weaker `:I` on the same hardwired address because both used the same priority.

There is **no single regex** that finds Slot/Card for every row: most AAX programs in this mill (communications, DAT routing, PID internals) never mention hardware. Those rows cannot be given a card without inventing data or reading a separate DB dump.

---

## 2. How Slot/Card Number is represented

Three representations appear in the corpus (none is `:ADDR`):

| Form | Where | Slot/Card meaning | Files |
|------|--------|-------------------|--------|
| `=AI7.10`, `=DO3.20`, `=DI2.23:BLOCKED` | PIDCON `:MV`, MOTCON `:MC`/`:M2`/`:SO1`, VALVECON `:CLS`, MOVE ports, AND/OR wires | The number after the family prefix is the AC450 I/O board / slot | `23JA1601`, `23JA1701`, `23JA1801` and PM3 twins with wiring |
| `:IOADDR 192` (also 193) | `PCU-I`, `PCU-O`, `PCU-COM` | Pulse-counter **module address** (Advant high I/O range) | `23JA1801`, `N221801` (14 addressed PCU-I/O pairs each) |
| Not present | Majority of PC diagrams | Physical assignment lives in the **DB** (`:ADDR` on AI1 / AI1.1), not in the PC AAX | 26 of 32 files |

No file in `.AXX Data` contains a `:ADDR` parameter. Controller vs I/O is split: PC AAX = application wiring; DB BAX = hardware cards.

---

## 3. How Channel Number is represented

| Form | Where | Channel meaning |
|------|--------|-----------------|
| `.10` in `=AI7.10` | Same token as slot | Channel on that board (1–32 typical) |
| `:CHANNEL 1` | Immediately under `:IOADDR` on `PCU-I` / `PCU-O` | Channel 1–4 on that pulse module |
| Absent | Soft / DAT / intra-PC tags | No channel stored in the AAX |

`PCU-COM` / `PCU-SS` list `:IOADDR` / `:IOADDR1..5` without `:CHANNEL`; those are module configuration, not per-signal I/O, and are not emitted as records.

---

## 4. New extraction strategy

Still emit `=CATcard.channel/DeviceTag` for the existing GrammarParser. Only the **address half** of that string changed.

```
4A  Hardwired =AIcard.ch (priority 5 for named ports MV/MC/SO1/CLS/M2/…, else 3)
4B  Soft dotted tags          → still CAT0.0 until join
4C  Colon-form tags
4D  :DBINST / named I/O params
4F  PCU-I / PCU-O             → Slot = :IOADDR, Channel = :CHANNEL
4G  Same-block join
      • named FB param + :DBINST or page title → identity.suffix @ that HW
      • MOVE pairs :21↔:22, :23↔:24, :11↔:12, :1↔:2 when one side is HW
        and the other is a plant tag (upgrades 82PIC972.POUT to AO3.9
        without deleting 82PIC972.OUT)
```

`CandidateSet.attach_address` updates a tag-keyed row so several device tags may share one physical channel.

Device tags, loop tags, and categories are not rewritten; a previously soft tag keeps its name and only gains card/channel.

---

## 5. Relationships discovered

| Engineering object | Hardware link |
|--------------------|----------------|
| PIDCON `:DBINST =82PIC972` + `:MV =AI7.10` | 82PIC972.MV ← AI slot 7 ch 10 |
| MOVE `:21 =82PIC972:POUT` + `:22 =AO3.9` | 82PIC972.POUT ← AO slot 3 ch 9 |
| VALVECON `:CLS =DO3.20` + loop 82HSV974 | 82HSV974.CLS ← DO slot 3 ch 20 |
| MOTCON `:M2 =DI1.32`, `:SO1 =DO1.25`, `:MC =AI1.25` | Motor loop 82M103 field I/O |
| PCU-I `:IOADDR 192` `:CHANNEL 1` on page `82M140: Reel Drum Speed` | 82M140.SPEEDMV ← slot 192 ch 1 |
| PCU-O same IOADDR/CHANNEL | 82M140.PULSEOUT ← slot 192 ch 1 |
| SW / DAT / `:11 =122F124A.B1` | No hardware in the AAX (inter-node dataset) |

Hardware config (`PCU-COM` module list) and engineering objects (page title + FB) live in **different blocks** and are joined by **page title** plus **IOADDR/CHANNEL**, not by a shared object id.

---

## 6. Validation against `.AXX Data`

Every unique `=AIcard.ch` / `=AOcard.ch` / `=DIcard.ch` / `=DOcard.ch` token in the corpus appears in Excel with that Slot and Channel (`hw_ok` on all 32 files).

| File | Excel rows | Rows with Slot>0 and Channel>0 | Unique `=CATn.m` in source | PCU `:IOADDR`+`:CHANNEL` pairs |
|------|------------|----------------------------------|----------------------------|--------------------------------|
| 23JA1601.AAX | 106 | 10 | 9 | 0 |
| 23JA1701.AAX | 71 | 1 | 1 | 0 |
| 23JA1801.AAX | 214 | 17 | 3 | 14 |
| N221701.AAX | 70 | 1 | 1 | 0 |
| N221801.AAX | 214 | 15 | 1 | 14 |
| All other 27 files | 1273 | 0 | 0 | 0 |
| **Corpus** | **1948** | **44** | **15 unique HW tokens** | **28** |

23JA1801: 3 field-bus tokens + 14 PCU I/O tags = **17** addressed rows (complete).  
23JA1601: 9 unique boards + MOVE POUT bind = **10** addressed rows.

Spot checks:

| Device Tag | Expected | Extracted |
|------------|----------|-----------|
| 82PIC972.MV | AI 7.10 | Slot 7, Channel 10 |
| 82PIC972.POUT | AO 3.9 | Slot 3, Channel 9 |
| 82HSV974.CLS | DO 3.20 | Slot 3, Channel 20 |
| 82M103.M2 | DI 1.32 | Slot 1, Channel 32 |
| 82M103.SO1 | DO 1.25 | Slot 1, Channel 25 |
| 82M140.SPEEDMV | IOADDR 192 CH 1 | Slot 192, Channel 1 |
| 82M140.PULSEOUT | IOADDR 192 CH 1 | Slot 192, Channel 1 |
| 82M136.SPEEDMV | IOADDR 192 CH 2 | Slot 192, Channel 2 |
| 82SIA958.SPEEDMV | IOADDR 193 CH 1 | Slot 193, Channel 1 |

PM3 twin `N221601.AAX` contains **no** `=AIx.y` strings (export difference vs `23JA1601.AAX`); the parser cannot invent boards that the file does not name. Unit tests: 40 passed including `test_pidcon_mv_and_move_pout_resolve_card_channel` and `test_pcu_ioaddr_channel_bound_to_speed_tag`.

---

## 7. Category confirmation

When hardware exists, Slot/Card and Channel now resolve for:

- **AI** — PIDCON `:MV`, MOTCON `:MC`, PCU-I `:IOADDR`/`:CHANNEL` (SPEEDMV)
- **AO** — MOVE `:22 =AOn.m` bound to `:POUT` / `.OUT`
- **DI** — MOTCON `:M2`, hardwired `=DIcard.ch`
- **DO** — VALVECON `:CLS`, MOTCON `:SO1`, PCU-O pulse, `=DOcard.ch`

**AI800_ / AO800_ / DI800_ / DO800_:** none of the 32 corpus files contain 800-series hardwired tokens. The `=AI800_card.ch` matcher is unchanged and will fill Slot/Channel if those strings appear.

Rows with Slot 0 remain **software / DAT / inter-loop** signals. The AAX does not store a board for them; filling those requires the matching DB Element (`:ADDR` on the card object), which is outside this PC AAX reader.

---

## Expected result (met)

For every supported I/O record whose Slot/Card and Channel are stored in the AAX — either as `=CATcard.channel` or as PCU `:IOADDR` + `:CHANNEL` — those values are now written to Excel. Where the AAX has no hardware section, values are not fabricated.
