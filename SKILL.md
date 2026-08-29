---
name: phoenix-studio
metadata:
  version: "0.1"
  phase: "8"
  note: "2026-08-29 Phase 8 — zoom+pan compose"
description: Phoenix Studio deterministic SaaS / UI motion renderer — contracts, validator, camera engine through Phase 8
---

คุณคือเอเจนต์ของ Phoenix Studio

## เฟสปัจจุบัน = 8

ตรวจแผนด้วย `python -m validator`
เรนเดอร์ด้วย `python -m renderer project.json -o out.mp4`
รองรับ `hold` `crop_9_16` `highlight_box` `spotlight_dim` `kinetic_text` `cursor_move` `cursor_click` `zoom_to_region` `pan_to_region` `USER_VOICE`

## กฎที่ห้ามหัก

- AI คิด เรนเดอร์เชื่อ
- AI ห้ามเขียนคำสั่ง FFmpeg ดิบ
- Timeline DSL เป็นกลางต่อเอนจิน
- เวลาเป็นมิลลิวินาทีจำนวนเต็ม
- พิกัดโปรเจกต์เป็น 0..1 จุดกำเนิดมุมซ้ายบน
- ชั้นความจริงกับชั้นบรรยากาศแยกกัน
- primitive ไม่รู้จักชื่อ = ใบสั่งตาย

อ่าน `references/ARCHITECTURE.md` ก่อนทำงานทุกครั้ง
