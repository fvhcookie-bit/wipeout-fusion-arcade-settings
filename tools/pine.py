"""Minimal PCSX2 PINE client (enable PINE in PCSX2: Settings -> Advanced -> PINE, port 28011)."""
import socket, struct


class PineError(Exception):
    pass

class Pine:
    """Minimal PINE client. Message: u32 total_size, then commands; reply: u32 size, u8 result, payload."""
    READ = {1: 0, 2: 1, 4: 2, 8: 3}
    MSG_VERSION, MSG_SAVE, MSG_LOAD, MSG_TITLE, MSG_ID, MSG_UUID, MSG_GAMEVER, MSG_STATUS = 8, 9, 10, 11, 12, 13, 14, 15

    def __init__(self, host='127.0.0.1', port=28011, timeout=2.0):
        self.addr = (host, port); self.timeout = timeout; self.sock = None

    def connect(self):
        self.close()
        s = socket.create_connection(self.addr, self.timeout)
        s.settimeout(self.timeout)
        self.sock = s

    def close(self):
        if self.sock:
            try: self.sock.close()
            except OSError: pass
        self.sock = None

    def _recv_exact(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk: raise PineError('connection closed by PCSX2')
            buf += chunk
        return buf

    def call(self, body):
        if self.sock is None: self.connect()
        self.sock.sendall(struct.pack('<I', len(body) + 4) + body)
        size = struct.unpack('<I', self._recv_exact(4))[0]
        rest = self._recv_exact(size - 4)
        if rest[0] != 0: raise PineError('PINE command failed (no game running / bad address?)')
        return rest[1:]

    def read_many(self, reqs):
        """reqs: list of (addr, width in bytes 1/2/4/8). Returns list of ints (unsigned)."""
        body = b''.join(struct.pack('<BI', self.READ[w], a) for a, w in reqs)
        data = self.call(body); out = []; o = 0
        fmt = {1: '<B', 2: '<H', 4: '<I', 8: '<Q'}
        for _, w in reqs:
            out.append(struct.unpack_from(fmt[w], data, o)[0]); o += w
        return out

    WRITE = {1: 4, 2: 5, 4: 6, 8: 7}

    def write_many(self, reqs):
        """reqs: list of (addr, width 1/2/4/8, value). Batched writes, one reply."""
        fmt = {1: '<B', 2: '<H', 4: '<I', 8: '<Q'}
        body = b''.join(struct.pack('<BI', self.WRITE[w], a) + struct.pack(fmt[w], v & ((1 << 8 * w) - 1))
                        for a, w, v in reqs)
        self.call(body)

    def _string(self, op):
        data = self.call(bytes([op]))
        n = struct.unpack_from('<I', data, 0)[0]
        return data[4:4 + n].split(b'\0')[0].decode('latin1')

    def version(self): return self._string(self.MSG_VERSION)
    def title(self): return self._string(self.MSG_TITLE)
    def game_id(self): return self._string(self.MSG_ID)
    def status(self): return struct.unpack('<I', self.call(bytes([self.MSG_STATUS]))[:4])[0]  # 0 run, 1 pause, 2 off
    def save_state(self, slot): self.call(bytes([self.MSG_SAVE, slot]))

# ----------------------------------------------------------------------------------------------- game knowledge
SHIP0, DYN0 = 0x2CC500, 0x2CC540
G = {  # name: (address, type)   — see docs/02_ship.md, 04_race_rules.md
    'frameMs': (0x27C1B8, 'u32'), 'gameMode': (0x3953D8, 'u32'), 'raceStarted': (0x27C1C0, 'u32'),
    'paused': (0x27C1C8, 'u32'), 'startSeq': (0x352E60, 'u32'), 'track': (0x27BB88, 'u32'),
    'env': (0x352E48, 'u8'), 'circuit': (0x352E49, 'u8'), 'class': (0x352E4A, 'u8'),
    'numShips': (0x352E4D, 'u8'), 'numLaps': (0x352E4E, 'u8'),
    'flags': (SHIP0 + 0xDA4, 'u32'), 'input': (SHIP0 + 0xD84, 'u32'), 'lap': (SHIP0 + 0xDA8, 's8'),
    'progress': (SHIP0 + 0xDAC, 'f32'), 'position': (SHIP0 + 0xDE8, 's32'), 'lapStartMs': (SHIP0 + 0xDB0, 'u32'),
    'lastLapMs': (SHIP0 + 0xDB4, 'u32'), 'bestLapMs': (SHIP0 + 0xDB8, 'u32'), 'pExtra': (SHIP0 + 0xE04, 'u32'),
    'posX': (DYN0 + 0x0, 'f32'), 'posY': (DYN0 + 0x4, 'f32'), 'posZ': (DYN0 + 0x8, 'f32'),
    'speed': (DYN0 + 0x294, 'f32'), 'shield': (DYN0 + 0x3AC, 'f32'),
    'dmgEngine': (DYN0 + 0x398, 'f32'), 'dmgNose': (DYN0 + 0x39C, 'f32'),
    'dmgStability': (DYN0 + 0x3A0, 'f32'), 'dmgAirbrakes': (DYN0 + 0x3A4, 'f32'),
    'weapon': (DYN0 + 0xCA4, 's32'), 'flipped': (DYN0 + 0x2F4, 's32'), 'flying': (DYN0 + 0x2D8, 's32'),
    'airJump': (DYN0 + 0x2D0, 's32'), 'fallenOff': (DYN0 + 0xC94, 's32'), 'grounded': (DYN0 + 0xC6C, 's32'),
    'speedUp': (DYN0 + 0x2FC, 's32'), 'surfaceIdx': (DYN0 + 0xB94, 's32'), 'nearSection': (DYN0 + 0xC78, 'u32'),
    'padHeld': (0x2CBE70, 'u32'), 'padEdge': (0x2CBE78, 'u32'),
}
GAME_MODES = ['undefined', 'SINGLE_ARCADE', 'SINGLE_TIMETRIAL', 'SINGLE_CHALLENGE', 'SINGLE_LEAGUE',
              'SINGLE_LEAGUE_CHALLENGE', 'SINGLE_ACADEMY', 'SINGLE_MULTIPLAYER', 'SINGLE_ELIMINATOR', 'SINGLE_ZONE',
              'SINGLE_ENDURANCE', 'SINGLE_OPTIONS', 'MULTI_ARCADE', 'MULTI_TIMETRIAL', 'MULTI_LEAGUE',
              'MULTI_ELIMINATOR', 'MULTI_ENDURANCE']
TRACKS = ['florion_height', 'mandrashee', 'cubiss_float', 'alca_vexus', 'vohl_square', 'temtesh_bay', 'katmoda_12',
          'devilia']
WEAPONS = ['TURBO', 'AUTOPILOT', 'ROCKET', 'MINES', 'MISSILE', 'QUAKE', 'GRAVITY_BOMB', 'SUPER_MISSILES',
           'ORBITAL_LASER', 'POWER_SWARM', 'SHIELD_DRAIN', 'NITRO_ROCKET', 'PENETRATOR', 'FLAMER', 'PLASMA_BOLT',
           'SEISMIC_FIELD', 'GRENADES', 'BIO_SNARE', 'AG_STINGER', 'PROTON_CANNON', 'SHIELD_RAIDER', 'HUNTER_MISSILE',
           'TURBO_ENFORCER', 'STEALTH', 'GLOBAL_DRAIN', 'SHIELD', 'CONTROL_JAMMER']
SURFACE_TABLE = 0x344F0C
TYPES = {'u8': (1, '<B'), 's8': (1, '<b'), 'u16': (2, '<H'), 's16': (2, '<h'), 'u32': (4, '<I'), 's32': (4, '<i'),
         'f32': (4, '<f')}
