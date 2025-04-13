import protocol.vid_v3 as v3
import protocol.vid_v2 as v2
import protocol.vid_v2_asecl as v2_asecl
import protocol.vid_v2_asecl_cp as v2_asecl_cp
import protocol.vid_v2_asecl_oven as v2_asecl_oven
import protocol.vid_v3_qual as v3_qual
import protocol.vid_v3_k25 as v3_k25
import protocol.vid_v3_biwin as v3_biwin
import protocol.vid_v3_mirle as v3_mirle
import protocol.vid_v3_CHIPMOS as v3_chipmos
import protocol.vid_v3_TICD as v3_ticd
import protocol.vid_v3_TIPI_TIEM as v3_tipi_tiem

protocol_list ={
    'v3': v3,
    'v2.7': v2,
    'v2_ASECL':v2_asecl,
    'v2_ASECL_CP':v2_asecl_cp,
    'v2_ASECL_OVEN':v2_asecl_oven,
    'v3_QUALCOMM':v3_qual,
    'v3_K25':v3_k25,
    'v3_BIWIN':v3_biwin,
    'v3_MIRLE':v3_mirle,
    'v3_CHIPMOS':v3_chipmos,
    'v3_TICD':v3_ticd,
    'v3_TIPI_TIEM':v3_tipi_tiem,
}
