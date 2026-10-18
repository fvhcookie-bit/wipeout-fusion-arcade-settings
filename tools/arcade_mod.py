# Generator for the "Arcade race settings" PCSX2 patch (WipEout Fusion PAL, SCES-50005, CRC 90DB90F1).
# The module grew in steps during development; later definitions override earlier ones (v3.x blocks at the end).
# `python arcade_mod.py pnach` prints the final patch section.
"""arcade_mod.py — single-player Arcade takes race settings from the two-player settings screen.

    python arcade_mod.py live      # write the patch into the running game via PINE (test, lasts until reboot)
    python arcade_mod.py check     # read back patch + current 2P settings
    python arcade_mod.py pnach     # print the pnach section

Hook: Race_DumpGameModeData_Q 0x199988, case GM_SINGLE_ARCADE ends with `b 0x19a034` at 0x199B48 (delay slot:
sw t7, dca8). We replace it with `j CAVE`; the cave overrides raceData (t0 = 0x352E48) from the 2P settings:
  numShipsInRace (+5)  = min(0x386A98 + 2, 16)     (2P menu: number of AI)
  numLapsInRace  (+6)  = 0x386A8C                  (2P menu: laps)
  flag10 pit     (+0x10) = 0x386A90 != 0           (2P menu: pit lane)
and puts the player's grid slot (event +0x70) at numShips - 1 so the grid has no gaps (AI fill 0..n-2).
The common tail at 0x19A034 uses only s2/s5/s6, so t8/t9/v0/v1 are free. Cave in the zero area below the ELF
(0x95064..0x100000 is zero in all 69 savestates).
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CAVE = 0x000FF000
HOOK = 0x00199B48
HOOK_ORIG = None  # filled from ELF check below (b 0x19a034)
ZERO, V0, V1, T0, T8, T9, GP = 0, 2, 3, 8, 24, 25, 28


def lui(rt, imm): return 0x3C000000 | rt << 16 | (imm & 0xFFFF)
def i_type(op, rs, rt, imm): return op << 26 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def lw(rt, off, rs): return i_type(0x23, rs, rt, off)
def lbu(rt, off, rs): return i_type(0x24, rs, rt, off)
def sb(rt, off, rs): return i_type(0x28, rs, rt, off)
def sw(rt, off, rs): return i_type(0x2B, rs, rt, off)
def addiu(rt, rs, imm): return i_type(0x09, rs, rt, imm)
def slti(rt, rs, imm): return i_type(0x0A, rs, rt, imm)
def bne(rs, rt, off): return i_type(0x05, rs, rt, off)
def sltu(rd, rs, rt): return rs << 21 | rt << 16 | rd << 11 | 0x2B
def addu(rd, rs, rt): return rs << 21 | rt << 16 | rd << 11 | 0x21
def mult(rs, rt): return rs << 21 | rt << 16 | 0x18
def mflo(rd): return rd << 11 | 0x12
def j(target): return 0x08000000 | (target >> 2) & 0x3FFFFFF
NOP = 0


def hi_lo(addr):
    lo = addr & 0xFFFF
    if lo >= 0x8000: lo -= 0x10000
    return (addr - lo) >> 16, lo


def cave_code():
    h, _ = hi_lo(0x386A98)
    assert hi_lo(0x386A8C)[0] == h and hi_lo(0x386A90)[0] == h
    eh, el = hi_lo(0x389EE8 + 0x70)
    c = [
        lui(T9, h),
        lw(T8, hi_lo(0x386A98)[1], T9),      # AI count
        addiu(T8, T8, 6),                    # ships = AI + 6: slider 0..10 -> 6..16 ships (2P Arcade itself is AI + 2)
        slti(V0, T8, 17),
        bne(V0, ZERO, 2),                    # -> store
        NOP,
        addiu(T8, ZERO, 16),
        sb(T8, 5, T0),                       # numShipsInRace
        lbu(V0, hi_lo(0x386A8C)[1], T9),     # laps
        sb(V0, 6, T0),
        lw(V0, hi_lo(0x386A90)[1], T9),      # pit lane on/off
        sltu(V0, ZERO, V0),
        sw(V0, 0x10, T0),
        lbu(V0, hi_lo(0x386A8F)[1], T9),     # CPU shield handicap -> slot of ship 1 (P2 handicap)
        sb(V0, hi_lo(0x386A8E)[1], T9),
        lw(V0, -0x42CC, GP),                 # event index (0x27DCA4)
        addiu(V1, ZERO, 0xE0),
        mult(V0, V1),
        mflo(V0),
        lui(V1, eh),
        addu(V0, V0, V1),
        addiu(T8, T8, -1),
        sb(T8, el, V0),                      # event +0x70: player grid slot = ships - 1
        j(0x0019A034),
        NOP,
    ]
    return c


# Respawn (2P setting 0x386A94): FUN_001ac2c0 (destruction sequence) allows it only when `iGameMode >= 12`.
# Three sites `lw r, mode; slti r, r, 0xc` -> `j SITE_CAVE; nop`; the cave returns r = 0 ("not single") in Arcade,
# otherwise the original `mode < 12`. Only r is clobbered.  (site, result reg, original lw, original slti)
RESPAWN_SITES = [(0x001AC880, V0, 0x8E0205F0, 0x2842000C),
                 (0x001ACA40, V0, 0x8C6253D8, 0x2842000C),
                 (0x001ACB80, V1, 0x8C8305F0, 0x2863000C)]
SITE_CAVE = 0x000FF080
AI_SLIDER = 0x0014CC78  # original 0x2402000A


def xori(rt, rs, imm): return i_type(0x0E, rs, rt, imm)
def beq(rs, rt, off): return i_type(0x04, rs, rt, off)


def site_code(r, back):
    return [lui(r, 0x39), lw(r, 0x53D8, r), xori(r, r, 1), beq(r, ZERO, 3), xori(r, r, 1),
            j(back), slti(r, r, 0xC), j(back), addu(r, ZERO, ZERO)]


def patches():
    out = [(CAVE + 4 * i, w) for i, w in enumerate(cave_code())]
    for k, (site, r, _, _) in enumerate(RESPAWN_SITES):
        base = SITE_CAVE + 0x40 * k
        out += [(base + 4 * i, w) for i, w in enumerate(site_code(r, site + 8))]
    # hooks last: code first, then the jumps into it
    out.append((HOOK, j(CAVE)))
    # 2P settings screen (FUN_0014c99c): AI-count slider built with 10 segments (`addiu v0,zero,10` = stack arg 9 of
    # FUN_0012aa3c). The widget's arrays hold exactly 14 segments (+0xC8..+0x100, +0x100..+0x138), value = 0..segments,
    # so 14 -> up to 14 AI -> 16 ships (both 2P Arcade and the patched single Arcade).
    # NOT USED: 14 segments overflow the main frame DMA buffer (0x27E278 block, 0x52090) on the 2P settings screen
    # (crash seen when toggling the pit option: VifPack_CloseDmaBlock "Bytes over"). Single Arcade maps AI+6 instead.
    for k, (site, r, _, _) in enumerate(RESPAWN_SITES):
        out += [(site, j(SITE_CAVE + 0x40 * k)), (site + 4, NOP)]
    return out


HOOKS = {HOOK} | {s for s, *_ in RESPAWN_SITES} | {s + 4 for s, *_ in RESPAWN_SITES}


# AI respawn (separate pnach section): FUN_001ac2c0 lets only human ships (flags & 1) respawn.
#  0x1ACA54 `andi v0,v0,1` -> `addiu v0,zero,1`: every ship enters the respawn branch (a94 && timer > 0x167 -> 0x19A reset)
#  0x1ACB98 `andi v0,v0,1` (after xori 1) -> `move v0,zero`: AI no longer gets Ship_Finish at 0x168 when respawn is on
# Works wherever respawn is allowed: 2P modes and (with the section above) single Arcade. FUN_001a9f58 restores the
# shield, clears destruction flags 0x32000; position is kept (same as the human respawn).
# After the reset the AI object still thinks it is wrecked (brakes, no throttle): the respawn call
# `jal FUN_001a9f58` at 0x1ACB48 (delay: move a0,s2) -> `jal AI_CAVE`; the cave calls FUN_001a9f58, then
# AI_RecoverFlip_Q 0x102938(pAI = ship+0xD94) for AI ships (the game's own "recover after flip/rescue" reset).
AI_CAVE = 0x000FF140
RA, SP, A0, S2 = 31, 29, 4, 18
def jal(t): return 0x0C000000 | (t >> 2) & 0x3FFFFFF
def jr(rs): return rs << 21 | 0x08
# Also clear flag 0x1000 (2nd destruction stage, set at +1.2 s, never cleared by the reset): stuck AI ships after
# respawn all had it (0x1402), driving ones not.
T1 = 9
def and_(rd, rs, rt): return rs << 21 | rt << 16 | rd << 11 | 0x24
# The real cause: the destruction handler (BLK_ShipSFX ~227) calls FUN_00102a18(pAI, 1) -> pAI+0x1039 = 1, and
# FUN_00101c68 then drops throttle every frame (brakes 0xC0). Nobody resets it -> clear it here.
AI_CAVE_CODE = [addiu(SP, SP, -16), sw(RA, 0, SP), jal(0x001A9F58), NOP, lw(A0, 0xD94, S2), beq(A0, ZERO, 7), NOP,
                lw(T0, 0xDA4, S2), addiu(T1, ZERO, -0x1001), and_(T0, T0, T1), sw(T0, 0xDA4, S2),
                jal(0x00102938), sb(ZERO, 0x1039, A0), lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)]
AI_RESPAWN = ([(AI_CAVE + 4 * i, None, w) for i, w in enumerate(AI_CAVE_CODE)] +
              [(0x001ACA54, 0x30420001, 0x24020001), (0x001ACB98, 0x30420001, 0x00001021),
               (0x001ACB48, jal(0x001A9F58), jal(AI_CAVE))])


def pnach_ai():
    lines = ['[ReFusion: respawn for AI ships]', 'author=ReFusion',
             'description=Соперники тоже воскрешаются, если в меню режима на двоих включено воскрешение (в одиночной Arcade — вместе с патчем настроек из меню на двоих).']
    lines += [f'patch=1,EE,{a:08x},word,{w:08x}' for a, _, w in AI_RESPAWN]
    return '\n'.join(lines) + '\n'


def pnach():
    lines = ['[ReFusion: Arcade settings from 2P menu]', 'author=ReFusion',
             'description=Одиночная Arcade берёт число кругов, число соперников, пит-лейн и воскрешение из меню настроек режима на двоих; ползунок соперников 0…10 даёт в одиночной Arcade от 6 до 16 кораблей.']
    lines += [f'patch=1,EE,{a:08x},word,{w:08x}' for a, w in patches()]
    return '\n'.join(lines) + '\n'


# ---- Arcade menu: the 2P race-settings screen after Arcade ship select (see 'menu' command for the graph layout).
# The graph (PDSA_DATA) is loaded to the heap by FE_LoadPdsaData_Q 0x1383C4 from FE_CreateScreenManager_Q:
# 0x13DC44 `jal 0x1383C4` (delay: move a0,s1 = mgr 0x294F08) -> `jal MENU_CAVE`; the cave calls the loader and then
# edits the graph (s1 = mgr survives the call). The screen registration that follows does not touch state 50.
MENU_HOOK, MENU_HOOK_ORIG, MENU_CAVE = 0x0013DC44, 0x0C04E0F1, 0x000FF200
T2, T3, T4, T5, T6, T7, S1 = 10, 11, 12, 13, 14, 15, 17
def sll(rd, rt, sa): return rt << 16 | rd << 11 | sa << 6
def ori(rt, rs, imm): return i_type(0x0D, rs, rt, imm)


def menu_code():
    def row(dst):  # t3 = transitions + states[dst_state].first * 12
        return [lw(T2, dst * 12, T0), sll(T3, T2, 3), sll(T4, T2, 2), addu(T3, T3, T4), addu(T3, T3, T1)]
    c = [addiu(SP, SP, -16), sw(RA, 0, SP), jal(0x001383C4), NOP,
         lw(T0, 4, S1), lw(T1, 8, S1)]
    body = row(50) + [
        addiu(T5, ZERO, 0x3A), sw(T5, 0, T3), addiu(T6, ZERO, 2), sw(T6, 4, T3), addiu(T7, ZERO, 23), sw(T7, 8, T3),
        addiu(T5, ZERO, 0x3B), sw(T5, 12, T3), sw(T6, 16, T3), addiu(T7, ZERO, 22), sw(T7, 20, T3),
        sw(T6, 50 * 12 + 4, T0), lui(T5, 0x0028), ori(T5, T5, 0xCB20), sw(T5, 50 * 12 + 8, T0)] + row(22) + [
        addiu(T7, ZERO, 50), sw(T7, 8, T3)]
    c += [beq(T0, ZERO, len(body) + 1), NOP] + body
    c += [lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)]
    return c


def menu_patches():
    return [(MENU_CAVE + 4 * i, w) for i, w in enumerate(menu_code())] + [(MENU_HOOK, jal(MENU_CAVE))]


def pnach_all():
    lines = ['[Arcade race settings]', 'author=fvhcookie-bit (ReFusion project)',
             'description=Single-player Arcade gets its own race set-up screen after ship select: laps, number of ships (6-16), player and CPU shield, CPU upgrade level / race class, pit lane, player respawn, catch-up, and what happens to destroyed CPU ships (out / respawn / wreck).']
    words = patches() + [(a, w) for a, _, w in AI_RESPAWN] + menu_patches() + screen_patches() + extra_patches()
    lines += [f'patch=1,EE,{a:08x},word,{w:08x}' for a, w in words]
    return '\n'.join(lines) + '\n'


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'pnach'
    if cmd == 'pnach':
        print(pnach_all(), end=''); return
    from pine import Pine
    p = Pine(); p.connect()
    print('game:', p.game_id(), p.title())
    if cmd == 'live':
        expect = {HOOK: 0x1000013A}
        for site, r, wl, ws in RESPAWN_SITES: expect[site] = wl; expect[site + 4] = ws
        want = dict(patches())
        for a, w0 in expect.items():
            cur = p.read_many([(a, 4)])[0]
            if cur not in (w0, want[a]):
                print(f'unexpected instruction at {a:08x}: {cur:08x}, aborting'); return
        p.write_many([(a, 4, w) for a, w in patches() if a not in HOOKS])
        p.write_many([(a, 4, w) for a, w in patches() if a in HOOKS])
        print('patched')
    if cmd == 'menu':
        # Frontend graph (PDSA_DATA, loaded to heap; mgr 0x294F08: +4 states {first,count,screen}, +8 transitions
        # {event(+0x3A applied), type 2=goto, target}). Spare state 50 (never targeted, unregistered) gets the 2P race
        # settings screen object 0x28CB20; Arcade ship select (state 22) accept -> 50 -> track select (23), back -> 22.
        M = 0x294F08; S = 50
        sp, tp = p.read_many([(M + 4, 4), (M + 8, 4)])
        f = p.read_many([(sp + S * 12, 4)])[0]
        f22 = p.read_many([(sp + 22 * 12, 4)])[0]
        if p.read_many([(tp + f22 * 12, 4)])[0] != 0x3A: print('unexpected graph, abort'); return
        p.write_many([(tp + f * 12, 4, 0x3A), (tp + f * 12 + 4, 4, 2), (tp + f * 12 + 8, 4, 23),
                      (tp + (f + 1) * 12, 4, 0x3B), (tp + (f + 1) * 12 + 4, 4, 2), (tp + (f + 1) * 12 + 8, 4, 22),
                      (sp + S * 12 + 4, 4, 2), (sp + S * 12 + 8, 4, 0x28CB20), (tp + f22 * 12 + 8, 4, S)])
        print('menu patched')
    if cmd == 'live-ai':
        for a, w0, w in AI_RESPAWN:
            cur = p.read_many([(a, 4)])[0]
            if w0 is not None and cur not in (w0, w): print(f'unexpected {a:08x}: {cur:08x}'); return
        p.write_many([(a, 4, w) for a, _, w in AI_RESPAWN]); print('AI respawn patched')
    vals = p.read_many([(HOOK, 4), (CAVE, 4), (0x386A98, 4), (0x386A8C, 1), (0x386A90, 4), (0x386A9C, 4), (0x386A94, 4)])
    print(f'hook {vals[0]:08x} cave0 {vals[1]:08x} | 2P menu: AI {vals[2]} laps {vals[3]} pit {vals[4]} catch-up {vals[5]} respawn {vals[6]}')



# ---- Arcade copy of the settings screen (rows of player 2 and split screen removed) -------------------------------
# A second instance of the 2P settings screen class at ARC_OBJ (free zone): class ctor FUN_0013b098 + screen init
# FUN_0014c99c(obj, ctx), constructed right after the game's own screens (FUN_001385c4 hook at 0x13DC54, ctx = a1),
# then state 50 -> ARC_OBJ and FUN_001384e0(mgr, ARC_OBJ, 50) for its button flags.
# Layout: the ctor computes 13 row y slots (+0xD84 + 4*i, step 0x1AD) right after its loop (0x14CA18 `lui s3,0x25`
# -> `jal LAYOUT_CAVE`, delay slot `addiu v0,fp,0x5C` kept); for ARC_OBJ rows 3..8 move up one slot, rows 2 (P2
# handicap, +0xD8C) and 9 (split screen, +0xDA8) go off screen (y = 8000).
# Cursor: rows 0..9 in +0xD44; the four up/down handlers end with `jal 0x14D3D8` (delay: move a0,s0) -> NAV caves
# skip rows 2 and 9 for ARC_OBJ.
ARC_OBJ = 0x000C0000
CTX_HOOK, CTX_HOOK_ORIG, CTX_CAVE = 0x0013DC54, 0x0C04E171, 0x000FF300
LAYOUT_HOOK, LAYOUT_HOOK_ORIG, LAYOUT_CAVE = 0x0014CA18, 0x3C130025, 0x000FF380
NAV_UP_SITES = [0x0014D6A4, 0x0014D794]
NAV_DOWN_SITES = [0x0014D718, 0x0014D824]
NAV_ORIG = 0x0C0534F6  # jal 0x14D3D8
NAV_UP_CAVE, NAV_DOWN_CAVE = 0x000FF400, 0x000FF500
A1, A2, S3, FP, OFFSCREEN = 5, 6, 19, 30, 8000


def bne_(rs, rt, off): return bne(rs, rt, off)


def asm(base, items):
    """items: words or ('label', name) or (op, *args, 'L:name') for branches; resolves branch offsets."""
    labels = {}; pc = base; flat = []
    for it in items:
        if isinstance(it, tuple) and it[0] == 'label': labels[it[1]] = pc; continue
        flat.append((pc, it)); pc += 4
    out = []
    for pc, it in flat:
        if isinstance(it, tuple):
            fn, *args = it
            args = [((labels[a[2:]] - (pc + 4)) >> 2) if isinstance(a, str) and a.startswith('L:') else a for a in args]
            out.append((pc, fn(*args)))
        else:
            out.append((pc, it))
    return out


def ctx_code():
    hi, lo = hi_lo(0x294F08)
    return asm(CTX_CAVE, [
        addiu(SP, SP, -32), sw(RA, 0, SP), sw(A1, 4, SP),
        jal(0x001385C4), NOP,                       # a0 set by the caller's delay slot (move a0,s1)
        lui(A0, ARC_OBJ >> 16), jal(0x0013B098), NOP,
        lui(A0, ARC_OBJ >> 16), jal(0x0014C99C), lw(A1, 4, SP),
        lui(T0, hi), lw(T0, lo + 4, T0), lui(T1, ARC_OBJ >> 16), sw(T1, 50 * 12 + 8, T0),
        lui(A0, hi), addiu(A0, A0, lo), lui(A1, ARC_OBJ >> 16), jal(0x001384E0), addiu(A2, ZERO, 50),
        lw(RA, 0, SP), jr(RA), addiu(SP, SP, 32)])


def layout_code():
    body = [lui(S3, 0x25), lui(T0, ARC_OBJ >> 16), (bne, FP, T0, 'L:done'), NOP]
    for off in (0xDA4, 0xDA0, 0xD9C, 0xD98, 0xD94, 0xD90):
        body += [lw(T1, off, FP), addiu(T1, T1, -0x1AD), sw(T1, off, FP)]
    body += [addiu(T1, ZERO, OFFSCREEN), sw(T1, 0xD8C, FP), sw(T1, 0xDA8, FP), ('label', 'done'), jr(RA), NOP]
    return asm(LAYOUT_CAVE, body)


def nav_code(base, maps):
    """For ARC_OBJ: each (from, to, fn, widget_off, arg1, arg2): cursor row from -> to, and un-highlight the row that
    the game's highlight function would leave lit (it only clears the original neighbours); then call it."""
    it = [addiu(SP, SP, -32), sw(RA, 0, SP), sw(A0, 4, SP), lui(T0, ARC_OBJ >> 16), (bne, A0, T0, 'L:go'), NOP]
    for k, (fr, to, fn, woff, x1, x2) in enumerate(maps):
        it += [lw(T1, 0xD44, A0), addiu(T2, ZERO, fr), (bne, T1, T2, f'L:n{k}'), NOP,
               addiu(T1, ZERO, to), sw(T1, 0xD44, A0),
               addiu(A0, A0, woff), addiu(A1, ZERO, x1), jal(fn), addiu(A2, ZERO, x2), lw(A0, 4, SP),
               ('label', f'n{k}')]
    it += [('label', 'go'), jal(0x0014D3D8), NOP, lw(RA, 0, SP), jr(RA), addiu(SP, SP, 32)]
    return asm(base, it)


BAR_HL, SLIDER_HL, TOGGLE_HL = 0x0012A7D4, 0x0012B580, 0x0012C178
NAV_UP_MAPS = [(9, 8, SLIDER_HL, 0x5C, 0, 10),      # wrapped from laps to the hidden split row: clear laps
               (2, 1, BAR_HL, 0x3B0, 0, 10)]        # CPU shield -> (hidden P2) -> P1 shield: clear CPU shield
NAV_DOWN_MAPS = [(2, 3, BAR_HL, 0x1A0, 0, 10),      # P1 shield -> (hidden P2) -> CPU shield: clear P1 shield
                 (9, 0, TOGGLE_HL, 0x8F8, 0, 0)]    # catch-up -> (hidden split) -> laps: clear catch-up


def screen_patches():
    out = ctx_code() + layout_code() + nav_code(NAV_UP_CAVE, NAV_UP_MAPS) + nav_code(NAV_DOWN_CAVE, NAV_DOWN_MAPS)
    out += [(CTX_HOOK, jal(CTX_CAVE)), (LAYOUT_HOOK, jal(LAYOUT_CAVE))]
    out += [(s, jal(NAV_UP_CAVE)) for s in NAV_UP_SITES] + [(s, jal(NAV_DOWN_CAVE)) for s in NAV_DOWN_SITES]
    return out


# ---- Handicaps, class, AI upgrade level in single Arcade ----------------------------------------------------------
# Same "single vs 2P" test (lw v0,mode; slti v0,v0,12) guards: race-start shield handicap FUN_001a97c8 (0x1A98B0),
# respawn shield handicap FUN_001a9f58 (0x1AA078), pit recharge cap FUN_0011c088 (0x11C144), class = aa8+1 in
# RaceInitialize (0x19AA6C). Arcade -> "2P" result 0 (site_code). Ship 1 would read the P2 handicap (0x386A8E):
# the race-setup cave copies the CPU handicap into it (side effect: the 2P menu P2 value follows the CPU one).
MODE_SITES = [(0x001A98B0, 0x8C6205F0), (0x001AA078, 0x8C6205F0), (0x0011C144, 0x8C6253D8), (0x0019AA6C, 0x8D0205F0)]
MODE_CAVE = 0x000FF600   # 4 x 0x40
# AI upgrades: after FUN_00199508 (race setup 0x19A0C0 `jal 0x199508`, delay nop) in Arcade every setup except the
# player's gets level = ceil((n-1)*pct/100) per group (n = setup+0x588, level at +0x570), pct = 0/34/67/100 by the
# 2P menu "upgrade level" (0x386AA8 = slider-1), like the 2P formula; the player keeps the profile levels.
UPG_HOOK, UPG_HOOK_ORIG, UPG_CAVE = 0x0019A0C0, 0x0C066542, 0x000FF700
# Screen enter FUN_0014d008: 0x14D058 `sw zero,0xd44(fp)` -> `jal TIER_CAVE` (ra already saved; a0 live -> kept):
# for ARC_OBJ preset the upgrade slider to the player's ship tier = FUN_00154f74()/25 (max 3), as the version pick.
TIER_HOOK, TIER_HOOK_ORIG, TIER_CAVE = 0x0014D058, 0xAFC00D44, 0x000FF800
T8_, T9_ = 24, 25
def div(rs, rt): return rs << 21 | rt << 16 | 0x1A
def slt(rd, rs, rt): return rs << 21 | rt << 16 | rd << 11 | 0x2A


def upg_code():
    return asm(UPG_CAVE, [
        addiu(SP, SP, -16), sw(RA, 0, SP), jal(0x00199508), NOP,
        lui(T0, 0x39), lw(T0, 0x53D8, T0), addiu(T1, ZERO, 1), (bne, T0, T1, 'L:done'), NOP,
        lui(T9_, 0x38), lw(T2, 0x6AA8, T9_),
        slt(T4, T2, ZERO), (beq, T4, ZERO, 'L:pos'), NOP, addiu(T2, ZERO, 0), ('label', 'pos'),
        sll(T3, T2, 5), addu(T3, T3, T2), sltu(T4, ZERO, T2), addu(T3, T3, T4),          # pct = 33*k + (k>0)
        lui(T5, 0x35), lbu(T6, 0x2E4B, T5), lbu(T7, 0x2E4C, T5),
        addiu(T6, T6, -1), sll(T6, T6, 1), addu(T6, T6, T7), addiu(T6, T6, -1),         # player setup index
        addiu(T0, ZERO, 0), lui(T1, 0x34), addiu(T1, T1, -0x3940),                      # 0x33C6C0
        ('label', 'loop'), (beq, T0, T6, 'L:next'), NOP, addiu(T2, ZERO, 0),
        ('label', 'g'), sll(T4, T2, 2), addu(T4, T4, T1), lw(T5, 0x588, T4), addiu(T5, T5, -1),
        mult(T5, T3), mflo(T5), addiu(T5, T5, 99), addiu(T7, ZERO, 100), div(T5, T7), mflo(T5), sw(T5, 0x570, T4),
        addiu(T2, T2, 1), slti(T4, T2, 6), (bne, T4, ZERO, 'L:g'), NOP,
        ('label', 'next'), addiu(T0, T0, 1), addiu(T1, T1, 0x6D0), slti(T4, T0, 16), (bne, T4, ZERO, 'L:loop'), NOP,
        ('label', 'done'), lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)])


def tier_code():
    return asm(TIER_CAVE, [
        addiu(SP, SP, -16), sw(RA, 0, SP), sw(A0, 4, SP), sw(ZERO, 0xD44, FP),
        lui(T0, ARC_OBJ >> 16), (bne, FP, T0, 'L:done'), NOP,
        jal(0x00154F74), NOP, addiu(T1, ZERO, 25), div(V0, T1), mflo(V0),
        slti(T1, V0, 4), (bne, T1, ZERO, 'L:ok'), NOP, addiu(V0, ZERO, 3), ('label', 'ok'),
        lui(T2, 0x38), sw(V0, 0x6AA8, T2),
        ('label', 'done'), lw(A0, 4, SP), lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)])


def extra_patches():
    out = []
    for k, (site, _) in enumerate(MODE_SITES):
        base = MODE_CAVE + 0x40 * k
        out += [(base + 4 * i, w) for i, w in enumerate(site_code(V0, site + 8))]
    out += upg_code() + tier_code()
    out += [(UPG_HOOK, jal(UPG_CAVE)), (TIER_HOOK, jal(TIER_CAVE))]
    for k, (site, _) in enumerate(MODE_SITES):
        out += [(site, j(MODE_CAVE + 0x40 * k)), (site + 4, NOP)]
    return out


# Upgrade slider limit: the enter handler caps it by the best-upgraded ship in the profile (FUN_0012acbc(slider, 1..4),
# +0xD4C). For ARC_OBJ allow all 4 levels (so the AI can be stronger than the player): 0x14D2E0 `jal 0x12af0c`
# (branch target; delay: lw a0,0xc(sp)) -> `jal MAX_CAVE`.
MAX_HOOK, MAX_HOOK_ORIG, MAX_CAVE = 0x0014D2E0, 0x0C04ABC3, 0x000FF880


def max_code():
    return asm(MAX_CAVE, [
        addiu(SP, SP, -16), sw(RA, 0, SP), sw(A0, 4, SP), lui(T0, ARC_OBJ >> 16), (bne, FP, T0, 'L:go'), NOP,
        addiu(A0, FP, 0x5FC), jal(0x0012ACBC), addiu(A1, ZERO, 4),
        addiu(A0, FP, 0x5FC), jal(0x0012ACC4), addiu(A1, ZERO, 100),
        addiu(T0, ZERO, 3), sw(T0, 0xD4C, FP),
        ('label', 'go'), lw(A0, 4, SP), lw(RA, 0, SP), j(0x0012AF0C), addiu(SP, SP, 16)])


_extra_patches_v1 = extra_patches
def extra_patches():
    return _extra_patches_v1() + max_code() + [(MAX_HOOK, jal(MAX_CAVE))]


# ---- v3: separate CPU-ship option "destroyed cpu ships": out / respawn / wreck ------------------------------------
# The hidden split-screen selector of ARC_OBJ (+0x9D4) comes back on screen (last slot) as a 3-option selector
# with custom texts; "respawn ships" (+0x81C, 2P setting 0x386A94) is relabelled "respawn player" and now only
# concerns the player. The CPU mode lives in MODEVAR (0 out, 1 respawn, 2 wreck; not saved, starts at 0 = original).
# Texts: FUN_00183b48(id) (300 callers) -> ids 0xF000.. answered from STR_TABLE (hook replaces its first 2 insns).
MODEVAR = 0x000FF9F0
STR_TABLE, STR_BASE = 0x000FF9C0, 0x000FFA00
STRINGS = ['respawn player', 'destroyed cpu ships', 'out', 'respawn', 'wreck']
TEXT_HOOK, TEXT_CAVE = 0x00183B48, 0x000FF900        # orig 3C02FFFF 3442FFFF
ENTER_HOOK, ENTER_CAVE = 0x0014D14C, 0x000FF940       # jal 0x12c128 (delay lw a0,8(sp) = +0x9D4 widget), fp = obj
APPLY_HOOK, APPLY_CAVE = 0x0014DAD8, 0x000FF960       # sw v0,0x80(s0) (aa0 store); fp = obj+0x5FC here
GATE_A, GATE_B = 0x001ACA50, 0x001ACB90               # lw v0,0xda4(s2) + next  -> j cave; nop
GATE_A_CAVE, GATE_B_CAVE = 0x000FFB00, 0x000FFB80
SHADOW_LOADS = [0x001ACA60, 0x001ACBA8]               # lw v1,0x6a94(v0) -> lw v1,0x6aa4(v0) (0x386AA4: free word)
SHADOW = 0x6AA4
S0 = 16


def andi(rt, rs, imm): return i_type(0x0C, rs, rt, imm)
def subu(rd, rs, rt): return rs << 21 | rt << 16 | rd << 11 | 0x23
CTX_CAVE = 0x000FFC00   # v3 ctx code is longer than the old slot
def sltiu(rt, rs, imm): return i_type(0x0B, rs, rt, imm)


def strings_patches():
    out = []; addr = STR_BASE
    for k, s_ in enumerate(STRINGS):
        out.append((STR_TABLE + 4 * k, addr))
        b = s_.encode('ascii') + b'\0'; b += b'\0' * (-len(b) % 4)
        for i in range(0, len(b), 4): out.append((addr + i, struct.unpack('<I', b[i:i + 4])[0]))
        addr += len(b)
    return out


def text_code():
    th, tl = hi_lo(STR_TABLE)
    return asm(TEXT_CAVE, [
        ori(V1, ZERO, 0xF000), subu(V1, A0, V1), sltiu(V0, V1, len(STRINGS)), (beq, V0, ZERO, 'L:orig'), NOP,
        sll(V1, V1, 2), lui(V0, th), addu(V0, V0, V1), jr(RA), lw(V0, tl, V0),
        ('label', 'orig'), lui(V0, 0xFFFF), ori(V0, V0, 0xFFFF), j(TEXT_HOOK + 8), NOP])


def enter_code():
    mh, ml = hi_lo(MODEVAR)
    return asm(ENTER_CAVE, [lui(T0, ARC_OBJ >> 16), (bne, FP, T0, 'L:go'), NOP, lui(A1, mh), lw(A1, ml, A1),
                            ('label', 'go'), j(0x0012C128), NOP])


def apply_code():
    mh, ml = hi_lo(MODEVAR)
    return asm(APPLY_CAVE, [lui(T0, ARC_OBJ >> 16), addiu(T0, T0, 0x5FC), (bne, FP, T0, 'L:orig'), NOP,
                            lui(T1, mh), jr(RA), sw(V0, ml, T1),
                            ('label', 'orig'), jr(RA), sw(V0, 0x80, S0)])


def gate_code(base, back, ret_v0):
    """shadow (0x386AA4) = respawn allowed for this ship: player -> 0x386A94; AI in Arcade -> MODEVAR != 0; else 0.
    A returns v0 = 'enter the respawn branch' (human or shadow); B returns v0 = 0 (0x1ACB98 zeroes it anyway)."""
    mh, ml = hi_lo(MODEVAR)
    it = [lw(T2, 0xDA4, S2), andi(T2, T2, 1), lui(T1, 0x38), (bne, T2, ZERO, 'L:human'), NOP,
          lui(T0, 0x39), lw(T0, 0x53D8, T0), addiu(T3, ZERO, 1), (bne, T0, T3, 'L:no'), NOP,
          lui(T0, mh), lw(T0, ml, T0), sltu(T0, ZERO, T0), sw(T0, SHADOW, T1), (beq, ZERO, ZERO, 'L:out'), NOP,
          ('label', 'no'), sw(ZERO, SHADOW, T1), addu(T0, ZERO, ZERO), (beq, ZERO, ZERO, 'L:out'), NOP,
          ('label', 'human'), lw(T0, 0x6A94, T1), sw(T0, SHADOW, T1), addiu(T0, ZERO, 1),
          ('label', 'out')]
    it += [addu(V0, ZERO, T0)] if ret_v0 else [addu(V0, ZERO, ZERO)]
    it += [j(back), NOP]
    return asm(base, it)


def ai_cave_v3():
    """wreck mode keeps the AI 'stopped' (no 0x1039 / 0x1000 clear, no recover) -> a standing wreck."""
    mh, ml = hi_lo(MODEVAR)
    return asm(AI_CAVE, [
        addiu(SP, SP, -16), sw(RA, 0, SP), jal(0x001A9F58), NOP, lw(A0, 0xD94, S2), (beq, A0, ZERO, 'L:end'), NOP,
        lui(T0, mh), lw(T0, ml, T0), addiu(T1, ZERO, 2), (beq, T0, T1, 'L:end'), NOP,
        lw(T0, 0xDA4, S2), addiu(T1, ZERO, -0x1001), and_(T0, T0, T1), sw(T0, 0xDA4, S2),
        jal(0x00102938), sb(ZERO, 0x1039, A0),
        ('label', 'end'), lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)])


AI_RESPAWN = ([(a, None, w) for a, w in ai_cave_v3()] +
              [(0x001ACB98, 0x30420001, 0x00001021), (0x001ACB48, jal(0x001A9F58), jal(AI_CAVE))])
NAV_UP_MAPS = [(2, 1, BAR_HL, 0x3B0, 0, 10)]
NAV_DOWN_MAPS = [(2, 3, BAR_HL, 0x1A0, 0, 10)]


def layout_code():
    body = [lui(S3, 0x25), lui(T0, ARC_OBJ >> 16), (bne, FP, T0, 'L:done'), NOP]
    for off in (0xDA8, 0xDA4, 0xDA0, 0xD9C, 0xD98, 0xD94, 0xD90):
        body += [lw(T1, off, FP), addiu(T1, T1, -0x1AD), sw(T1, off, FP)]
    body += [addiu(T1, ZERO, OFFSCREEN), sw(T1, 0xD8C, FP), ('label', 'done'), jr(RA), NOP]
    return asm(LAYOUT_CAVE, body)


def ctx_code():
    hi, lo = hi_lo(0x294F08)
    return asm(CTX_CAVE, [
        addiu(SP, SP, -32), sw(RA, 0, SP), sw(A1, 4, SP),
        jal(0x001385C4), NOP,
        lui(A0, ARC_OBJ >> 16), jal(0x0013B098), NOP,
        lui(A0, ARC_OBJ >> 16), jal(0x0014C99C), lw(A1, 4, SP),
        lui(T0, hi), lw(T0, lo + 4, T0), lui(T1, ARC_OBJ >> 16), sw(T1, 50 * 12 + 8, T0),
        # labels and the 3-option CPU selector
        lui(T0, ARC_OBJ >> 16), ori(T1, ZERO, 0xF000), sw(T1, 0x81C + 0x88, T0),
        ori(T1, ZERO, 0xF001), sw(T1, 0x9D4 + 0x88, T0),
        addiu(T2, ZERO, 3), sw(T2, 0x9D4 + 0x9C, T0), addiu(T2, ZERO, 2), sw(T2, 0x9D4 + 0xD8, T0),
        sw(T2, 0x9D4 + 0x94, T0), addiu(T2, ZERO, 1), sw(T2, 0x9D4 + 0x98, T0),
        ori(T1, ZERO, 0xF002), sw(T1, 0x9D4 + 0x48, T0), ori(T1, ZERO, 0xF003), sw(T1, 0x9D4 + 0x54, T0),
        ori(T1, ZERO, 0xF004), sw(T1, 0x9D4 + 0x60, T0),
        lw(T2, 0x9D4 + 0x58, T0), addiu(T2, T2, -0x5DC), sw(T2, 0x9D4 + 0x64, T0),
        lw(T2, 0x9D4 + 0x5C, T0), sw(T2, 0x9D4 + 0x68, T0),
        lui(A0, hi), addiu(A0, A0, lo), lui(A1, ARC_OBJ >> 16), jal(0x001384E0), addiu(A2, ZERO, 50),
        lw(RA, 0, SP), jr(RA), addiu(SP, SP, 32)])


def v3_patches():
    out = strings_patches() + text_code() + enter_code() + apply_code()
    out += gate_code(GATE_A_CAVE, GATE_A + 8, True) + gate_code(GATE_B_CAVE, GATE_B + 8, False)
    out += [(TEXT_HOOK, j(TEXT_CAVE)), (TEXT_HOOK + 4, NOP), (ENTER_HOOK, jal(ENTER_CAVE)),
            (APPLY_HOOK, jal(APPLY_CAVE)), (GATE_A, j(GATE_A_CAVE)), (GATE_A + 4, NOP),
            (GATE_B, j(GATE_B_CAVE)), (GATE_B + 4, NOP)]
    out += [(a, 0x8C430000 | SHADOW) for a in SHADOW_LOADS]
    return out


_extra_patches_v2 = extra_patches
def extra_patches():
    return _extra_patches_v2() + v3_patches()


# v3.1: row labels are baked when the widget is created (changing +0x88 later has no effect), so while ARC_OBJ is
# being built (ctx cave sets ARC_BUILD) the text lookup maps 0x70 'split screen' -> 0xF001 and 0x6D
# 'respawn ships' -> 0xF000.
ARC_BUILD = 0x000FF9F4
TEXT_CAVE = 0x000FFD00   # the longer v3.1 lookup no longer fits the old slot


def text_code():
    th, tl = hi_lo(STR_TABLE); fh, fl = hi_lo(ARC_BUILD)
    return asm(TEXT_CAVE, [
        lui(T0, fh), lw(T0, fl, T0), (beq, T0, ZERO, 'L:norm'), NOP,
        addiu(T1, ZERO, 0x70), (bne, A0, T1, 'L:c2'), NOP, ori(A0, ZERO, 0xF001), (beq, ZERO, ZERO, 'L:norm'), NOP,
        ('label', 'c2'), addiu(T1, ZERO, 0x6D), (bne, A0, T1, 'L:norm'), NOP, ori(A0, ZERO, 0xF000),
        ('label', 'norm'), ori(V1, ZERO, 0xF000), subu(V1, A0, V1), sltiu(V0, V1, len(STRINGS)),
        (beq, V0, ZERO, 'L:orig'), NOP,
        sll(V1, V1, 2), lui(V0, th), addu(V0, V0, V1), jr(RA), lw(V0, tl, V0),
        ('label', 'orig'), lui(V0, 0xFFFF), ori(V0, V0, 0xFFFF), j(TEXT_HOOK + 8), NOP])


_ctx_code_v3 = ctx_code
def ctx_code():
    fh, fl = hi_lo(ARC_BUILD)
    code = [w for _, w in _ctx_code_v3()]
    # insert "ARC_BUILD = 1" before `lui a0,0xC; jal 0x14C99C` and "= 0" right after its delay slot
    i = code.index(jal(0x0014C99C)) - 1
    code = code[:i] + [lui(T0, fh), addiu(T1, ZERO, 1), sw(T1, fl, T0)] + code[i:i + 3] + \
           [lui(T0, fh), sw(ZERO, fl, T0)] + code[i + 3:]
    return [(CTX_CAVE + 4 * k, w) for k, w in enumerate(code)]


# v3.2: FUN_0012b88c passes the label id to the text element as a halfword (lh a3,0x88(s4)) and resolves it at draw
# time -> custom ids must be < 0x8000 and set *before* creation. Ids now 0x7F00.., and FUN_0012b88c's
# `sw s2,0x88(s4)` (0x12B8E4, after ra is saved; delay `addiu t3,s1,-2`) -> `jal LABEL_CAVE` swaps the label id for
# the two ARC_OBJ widgets.
ID0 = 0x7F00
LABEL_HOOK, LABEL_HOOK_ORIG, LABEL_CAVE = 0x0012B8E4, 0xAE920088, 0x000FFD80
S4, T4_, T5_ = 20, 12, 13


def text_code():
    th, tl = hi_lo(STR_TABLE)
    return asm(TEXT_CAVE, [
        addiu(V1, A0, -ID0), sltiu(V0, V1, len(STRINGS)), (beq, V0, ZERO, 'L:orig'), NOP,
        sll(V1, V1, 2), lui(V0, th), addu(V0, V0, V1), jr(RA), lw(V0, tl, V0),
        ('label', 'orig'), lui(V0, 0xFFFF), ori(V0, V0, 0xFFFF), j(TEXT_HOOK + 8), NOP])


def label_code():
    return asm(LABEL_CAVE, [
        lui(T4_, ARC_OBJ >> 16), addiu(T5_, T4_, 0x9D4), (bne, S4, T5_, 'L:c2'), NOP,
        addiu(18, ZERO, ID0 + 1), (beq, ZERO, ZERO, 'L:out'), NOP,
        ('label', 'c2'), addiu(T5_, T4_, 0x81C), (bne, S4, T5_, 'L:out'), NOP, addiu(18, ZERO, ID0),
        ('label', 'out'), jr(RA), sw(18, 0x88, S4)])


def ctx_code():   # v3 ctx (no build flag), option ids moved to ID0+2..
    code = [w for _, w in _ctx_code_v3()]
    rep = {ori(T1, ZERO, 0xF000 + k): ori(T1, ZERO, ID0 + k) for k in range(5)}
    return [(CTX_CAVE + 4 * k, rep.get(w, w)) for k, w in enumerate(code)]


_extra_patches_v3 = extra_patches
def extra_patches():
    return _extra_patches_v3() + label_code() + [(LABEL_HOOK, jal(LABEL_CAVE))]


# v3.3: background title of ARC_OBJ (+0x1C text id, read every frame) -> 'race set-up'; P1 shield bar label
# (FUN_00129eb8 stores it at 0x12A078 `sw v1,0x74(s4)` before creating the halfword text element; ra saved;
# delay `move t2,zero`) -> 'shield energy player' for the ARC_OBJ+0x1A0 bar.
STRINGS = ['respawn player', 'destroyed cpu ships', 'out', 'respawn', 'wreck', 'race set-up', 'shield energy player']
BAR_HOOK, BAR_HOOK_ORIG, BAR_CAVE = 0x0012A078, 0xAE830074, 0x000FFDC0


def bar_code():
    return asm(BAR_CAVE, [lui(T4_, ARC_OBJ >> 16), addiu(T5_, T4_, 0x1A0), (bne, S4, T5_, 'L:out'), NOP,
                          addiu(V1, ZERO, ID0 + 6), ('label', 'out'), jr(RA), sw(V1, 0x74, S4)])


_ctx_code_v32 = ctx_code
def ctx_code():
    code = [w for _, w in _ctx_code_v32()]
    code = code[:-3] + [lui(T0, ARC_OBJ >> 16), addiu(T1, ZERO, ID0 + 5), sw(T1, 0x1C, T0)] + code[-3:]
    return [(CTX_CAVE + 4 * k, w) for k, w in enumerate(code)]


_extra_patches_v32 = extra_patches
def extra_patches():
    return _extra_patches_v32() + bar_code() + [(BAR_HOOK, jal(BAR_CAVE))]


# v3.4: wreck = really dead: AI off (flags |= 0x40: AI_ShipUpdate_Q then writes no controls; physics keeps it
# hovering), controls cleared like the player's at destruction (input/analog 0, +0xD92/+0xD93 = 0xFF), and pressed
# to the track like under AG Stinger (rideHeightAdjuster ship+0x350 = -2.5; only the Stinger code changes it).
def ai_cave_v4():
    mh, ml = hi_lo(MODEVAR)
    return asm(AI_CAVE, [
        addiu(SP, SP, -16), sw(RA, 0, SP), jal(0x001A9F58), NOP, lw(A0, 0xD94, S2), (beq, A0, ZERO, 'L:end'), NOP,
        lui(T0, mh), lw(T0, ml, T0), addiu(T1, ZERO, 2), (bne, T0, T1, 'L:normal'), NOP,
        lw(T0, 0xDA4, S2), ori(T0, T0, 0x40), sw(T0, 0xDA4, S2),
        sw(ZERO, 0xD84, S2), sw(ZERO, 0xD88, S2), sw(ZERO, 0xD8C, S2), sb(ZERO, 0xD90, S2), sb(ZERO, 0xD91, S2),
        addiu(T1, ZERO, 0xFF), sb(T1, 0xD92, S2), sb(T1, 0xD93, S2),
        lui(T1, 0xC020), sw(T1, 0x350, S2), (beq, ZERO, ZERO, 'L:end'), NOP,
        ('label', 'normal'),
        lw(T0, 0xDA4, S2), addiu(T1, ZERO, -0x1001), and_(T0, T0, T1), sw(T0, 0xDA4, S2),
        jal(0x00102938), sb(ZERO, 0x1039, A0),
        ('label', 'end'), lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)])


AI_RESPAWN = ([(a, None, w) for a, w in ai_cave_v4()] +
              [(0x001ACB98, 0x30420001, 0x00001021), (0x001ACB48, jal(0x001A9F58), jal(AI_CAVE))])


# v3.5: player ships also have an AI object (autopilot) -> the respawn cave must skip humans (flags & 1); the
# ride-height press (-2.5) sank wrecks/ships through the track -> removed.
def ai_cave_v5():
    mh, ml = hi_lo(MODEVAR)
    return asm(AI_CAVE, [
        addiu(SP, SP, -16), sw(RA, 0, SP), jal(0x001A9F58), NOP, lw(A0, 0xD94, S2), (beq, A0, ZERO, 'L:end'), NOP,
        lw(T0, 0xDA4, S2), andi(T0, T0, 1), (bne, T0, ZERO, 'L:end'), NOP,
        lui(T0, mh), lw(T0, ml, T0), addiu(T1, ZERO, 2), (bne, T0, T1, 'L:normal'), NOP,
        lw(T0, 0xDA4, S2), ori(T0, T0, 0x40), sw(T0, 0xDA4, S2),
        sw(ZERO, 0xD84, S2), sw(ZERO, 0xD88, S2), sw(ZERO, 0xD8C, S2), sb(ZERO, 0xD90, S2), sb(ZERO, 0xD91, S2),
        addiu(T1, ZERO, 0xFF), sb(T1, 0xD92, S2), sb(T1, 0xD93, S2), (beq, ZERO, ZERO, 'L:end'), NOP,
        ('label', 'normal'),
        lw(T0, 0xDA4, S2), addiu(T1, ZERO, -0x1001), and_(T0, T0, T1), sw(T0, 0xDA4, S2),
        jal(0x00102938), sb(ZERO, 0x1039, A0),
        ('label', 'end'), lw(RA, 0, SP), jr(RA), addiu(SP, SP, 16)])


AI_RESPAWN = ([(a, None, w) for a, w in ai_cave_v5()] +
              [(0x001ACB98, 0x30420001, 0x00001021), (0x001ACB48, jal(0x001A9F58), jal(AI_CAVE))])


# v3.6: flag 0x40 also removes the ship from ship-to-ship collisions (ShipToShipCollision_Q skips 0x40) -> wrecks were
# ghosts. Use the free flag bit 0x20 (never tested anywhere) as "wreck" and make AI_ShipUpdate_Q's AI-off test
# (0x101860 `andi v0,v0,0x40`) test 0x60: the AI writes no controls, collisions stay.
WRECK_BIT = 0x20
AIOFF_TEST = (0x00101860, 0x30420040, 0x30420060)


def ai_cave_v6():
    return [(a, w if w != ori(T0, T0, 0x40) else ori(T0, T0, WRECK_BIT)) for a, w in ai_cave_v5()]


AI_RESPAWN = ([(a, None, w) for a, w in ai_cave_v6()] +
              [(0x001ACB98, 0x30420001, 0x00001021), (0x001ACB48, jal(0x001A9F58), jal(AI_CAVE)), AIOFF_TEST])


if __name__ == '__main__':
    main()
