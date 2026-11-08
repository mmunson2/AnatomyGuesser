"""Curated list of guessable structures, resolved against BodyParts3D.

Each target is (id, system, budget, selectors). A selector is one of:
  "concept name"   – a concept from the IS-A or PART-OF element tables
  "re:<regex>"     – matched against each element file's English name

Targets claim elements in list order, so put specific structures before the
broader ones that contain them (mandible before skull, rectum before large
intestine). `budget` is the triangle cap for the merged, decimated mesh.

CONTEXT entries are drawn for orientation but never asked about.
"""

ORGAN, BIG_BONE, SMALL_BONE = 4000, 1800, 500
ARTERY, BIG_ARTERY = 1000, 1600

TARGETS = [
    # nervous
    ("cerebrum", "nervous", 8000, ["left cerebral hemisphere", "right cerebral hemisphere"]),
    ("cerebellum", "nervous", ORGAN, ["cerebellum"]),
    ("brainstem", "nervous", ORGAN, ["brainstem"]),
    ("eye", "nervous", 1500, ["left eyeball", "right eyeball"]),

    # cardiovascular / respiratory
    ("heart", "cardiovascular", 8000, ["heart"]),
    ("aorta", "cardiovascular", ORGAN, ["aorta"]),
    ("vena_cava", "cardiovascular", ORGAN, ["re:^(inferior|superior) vena cava$"]),
] + [
    # Major arteries, matched by element name: the PART-OF artery concepts
    # include every branch downstream ("left subclavian artery" holds the
    # whole arm). Before the liver, which holds the hepatic artery proper.
    # The coronary arteries stay part of the heart. BodyParts3D has no
    # external carotid or fibular artery, and its internal carotid stops
    # 6 cm short of the common carotid: see ZANATOMY_TARGETS.
    (pid, "cardiovascular", budget, ["re:^(trunk of )?(left |right )?(" + names + ")$"])
    for pid, budget, names in [
        ("pulmonary_trunk", ARTERY, "pulmonary trunk|pulmonary artery"),
        ("brachiocephalic_trunk", ARTERY, "brachiocephalic artery"),
        ("common_carotid", ARTERY, "common carotid artery"),
        ("vertebral_artery", ARTERY, "vertebral artery"),
        ("basilar_artery", ARTERY, "basilar artery"),
        ("subclavian_artery", ARTERY, "subclavian artery"),
        ("axillary_artery", ARTERY, "axillary artery"),
        ("brachial_artery", ARTERY, "brachial artery"),
        ("radial_artery", ARTERY, "radial artery"),
        ("ulnar_artery", ARTERY, "ulnar artery"),
        ("palmar_arches", ARTERY, "deep palmar arch|superficial palmar arterial arch"),
        ("celiac_trunk", ARTERY, "celiac trunk|celiac artery"),
        ("splenic_artery", ARTERY, "splenic artery"),
        ("hepatic_artery", ARTERY, "common hepatic artery|hepatic artery proper"),
        ("superior_mesenteric_artery", ARTERY, "superior mesenteric artery"),
        ("inferior_mesenteric_artery", ARTERY, "inferior mesenteric artery"),
        ("renal_artery", ARTERY, "renal artery"),
        ("common_iliac_artery", ARTERY, "common iliac artery"),
        ("internal_iliac_artery", ARTERY, "internal iliac artery"),
        ("external_iliac_artery", ARTERY, "external iliac artery"),
        ("femoral_artery", BIG_ARTERY, "femoral artery"),
        ("popliteal_artery", ARTERY, "popliteal artery"),
        ("anterior_tibial_artery", BIG_ARTERY, "anterior tibial artery"),
        ("posterior_tibial_artery", BIG_ARTERY, "posterior tibial artery"),
        ("dorsalis_pedis_artery", ARTERY, "dorsalis pedis artery"),
    ]
] + [
    # Major veins, matched by element name like the arteries. Their ids end
    # in _vein(s), which the viewer colours blue. The deep veins that just
    # shadow an artery (tibial, fibular, radial, ulnar) are left out, and the
    # hepatic veins stay part of the liver. BodyParts3D has no external
    # jugular: see ZANATOMY_TARGETS.
    (pid, "cardiovascular", ARTERY, ["re:^(left |right )?(" + names + ")$"])
    for pid, names in [
        ("internal_jugular_vein", "internal jugular vein"),
        ("brachiocephalic_vein", "brachiocephalic vein"),
        ("subclavian_vein", "subclavian vein"),
        ("axillary_vein", "axillary vein"),
        ("cephalic_vein", "cephalic vein"),
        ("basilic_vein", "basilic vein"),
        ("median_cubital_vein", "median cubital vein"),
        ("pulmonary_veins", "(superior|inferior) pulmonary vein"),
        ("azygos_vein", "azygos vein"),
        ("hepatic_portal_vein", "(pre-)?hepatic portal vein"),
        ("splenic_vein", "splenic vein"),
        ("superior_mesenteric_vein", "superior mesenteric vein"),
        ("renal_vein", "renal vein"),
        ("common_iliac_vein", "common iliac vein"),
        ("internal_iliac_vein", "internal iliac vein"),
        ("external_iliac_vein", "external iliac vein"),
        ("femoral_vein", "femoral vein"),
        ("popliteal_vein", "popliteal vein"),
        ("great_saphenous_vein", "great saphenous vein"),
        ("small_saphenous_vein", "small saphenous vein"),
    ]
] + [
    ("lungs", "respiratory", 12000, ["right lung", "left lung"]),
    ("trachea", "respiratory", 1500, ["trachea"]),

    # digestive
    ("tongue", "digestive", 1500, ["tongue"]),
    ("esophagus", "digestive", 1500, ["esophagus"]),
    ("stomach", "digestive", ORGAN, ["stomach"]),
    ("liver", "digestive", 6000, ["liver"]),
    ("gallbladder", "digestive", 1500, ["gallbladder"]),
    ("pancreas", "digestive", ORGAN, ["pancreas"]),
    ("spleen", "digestive", 2000, ["spleen"]),
    ("duodenum", "digestive", 2000, ["duodenum"]),
    ("small_intestine", "digestive", 10000, ["small intestine"]),
    ("appendix", "digestive", 800, ["appendix"]),
    ("rectum", "digestive", 1500, ["rectum"]),
    ("large_intestine", "digestive", 6000, ["large intestine"]),
    ("diaphragm", "muscular", ORGAN, ["diaphragm"]),

    # urinary / reproductive / endocrine
    ("kidney", "urinary", 3000, ["kidney"]),
    ("adrenal_gland", "endocrine", 1000, ["adrenal gland"]),
    ("ureter", "urinary", 1000, ["ureter"]),
    ("bladder", "urinary", 2000, ["urinary bladder"]),
    ("prostate", "reproductive", 1000, ["prostate"]),
    ("testis", "reproductive", 1000, ["testis"]),

    # skull
    ("mandible", "skeletal", BIG_BONE, ["mandible"]),
    ("frontal_bone", "skeletal", BIG_BONE, ["frontal bone"]),
    ("parietal_bone", "skeletal", BIG_BONE, ["re:^(left |right )?parietal bone$"]),
    ("temporal_bone", "skeletal", BIG_BONE, ["re:^(left |right )?temporal bone$"]),
    ("occipital_bone", "skeletal", BIG_BONE, ["occipital bone"]),
    ("zygomatic_bone", "skeletal", SMALL_BONE, ["re:^(left |right )?zygomatic bone$"]),
    ("maxilla", "skeletal", BIG_BONE, ["re:^(left |right )?maxilla$"]),
    ("nasal_bone", "skeletal", 300, ["re:^(left |right )?nasal bone$"]),
    ("hyoid", "skeletal", SMALL_BONE, ["hyoid bone"]),

    # axial
    ("cervical_vertebrae", "skeletal", 4000, ["cervical vertebra", "re:^atlas$", "re:^axis$"]),
    ("thoracic_vertebrae", "skeletal", 6000, ["thoracic vertebra"]),
    ("lumbar_vertebrae", "skeletal", 4000, ["lumbar vertebra"]),
    ("sacrum", "skeletal", BIG_BONE, ["sacrum"]),
    ("sternum", "skeletal", BIG_BONE, ["sternum"]),
    ("ribs", "skeletal", 8000, ["rib"]),
    ("costal_cartilage", "skeletal", 3000, ["costal cartilage"]),

    # upper limb
    ("clavicle", "skeletal", BIG_BONE, ["clavicle"]),
    ("scapula", "skeletal", BIG_BONE, ["scapula"]),
    ("humerus", "skeletal", BIG_BONE, ["humerus"]),
    ("radius", "skeletal", BIG_BONE, ["radius"]),
    ("ulna", "skeletal", BIG_BONE, ["ulna"]),
    ("carpals", "skeletal", 3000, ["carpal bone"]),
    ("metacarpals", "skeletal", 2500, ["metacarpal bone"]),
    ("finger_phalanges", "skeletal", 4000, ["re:phalanx of .*(finger|thumb)$"]),

    # lower limb
    ("hip_bone", "skeletal", 3000, ["hip bone"]),
    ("femur", "skeletal", BIG_BONE, ["femur"]),
    ("patella", "skeletal", SMALL_BONE, ["patella"]),
    ("tibia", "skeletal", BIG_BONE, ["tibia"]),
    ("fibula", "skeletal", BIG_BONE, ["fibula"]),
    ("calcaneus", "skeletal", SMALL_BONE * 2, ["re:^(left |right )?calcaneus$"]),
    ("talus", "skeletal", SMALL_BONE * 2, ["re:^(left |right )?talus$"]),
    ("tarsals", "skeletal", 2500, ["tarsal bone"]),
    ("metatarsals", "skeletal", 2500, ["metatarsal bone"]),
    ("toe_phalanges", "skeletal", 4000, ["re:phalanx of .*toe$"]),
]


def muscle(*names):
    """Selector for every element of a muscle: whole, left/right, or any
    head/part of it ("long head of left biceps brachii")."""
    return ["re:(^| )(left |right )?(" + "|".join(names) + ")( muscle)?$"]


MUSCLE, BIG_MUSCLE = 1500, 2500

TARGETS += [
    # neck / shoulder girdle
    ("sternocleidomastoid", "muscular", MUSCLE, muscle("sternocleidomastoid")),
    ("trapezius", "muscular", BIG_MUSCLE, muscle("trapezius")),
    ("deltoid", "muscular", BIG_MUSCLE, muscle("deltoid")),
    ("pectoralis_major", "muscular", BIG_MUSCLE, muscle("pectoralis major")),
    ("pectoralis_minor", "muscular", MUSCLE, muscle("pectoralis minor")),
    ("serratus_anterior", "muscular", BIG_MUSCLE, muscle("serratus anterior")),
    ("rhomboids", "muscular", MUSCLE, muscle("rhomboid major", "rhomboid minor")),
    ("levator_scapulae", "muscular", MUSCLE, muscle("levator scapulae")),
    ("supraspinatus", "muscular", MUSCLE, muscle("supraspinatus")),
    ("infraspinatus", "muscular", MUSCLE, muscle("infraspinatus")),
    ("teres_major", "muscular", MUSCLE, muscle("teres major")),
    ("teres_minor", "muscular", MUSCLE, muscle("teres minor")),
    ("subscapularis", "muscular", MUSCLE, muscle("subscapularis")),

    # arm
    ("biceps_brachii", "muscular", BIG_MUSCLE, muscle("biceps brachii")),
    ("triceps_brachii", "muscular", BIG_MUSCLE, muscle("triceps brachii")),
    ("brachialis", "muscular", MUSCLE, muscle("brachialis")),
    ("coracobrachialis", "muscular", MUSCLE, muscle("coracobrachialis")),
    ("brachioradialis", "muscular", MUSCLE, muscle("brachioradialis")),
    ("forearm_flexors", "muscular", 4000, muscle(
        "flexor carpi radialis", "flexor carpi ulnaris", "palmaris longus",
        "flexor digitorum superficialis", "flexor digitorum profundus",
        "flexor pollicis longus", "pronator teres", "pronator quadratus")),
    ("forearm_extensors", "muscular", 4000, muscle(
        "extensor carpi radialis longus", "extensor carpi radialis brevis",
        "extensor carpi ulnaris", "extensor digitorum", "extensor digiti minimi",
        "extensor indicis", "extensor pollicis longus", "extensor pollicis brevis",
        "abductor pollicis longus", "supinator", "anconeus")),

    # trunk
    ("external_oblique", "muscular", BIG_MUSCLE, muscle("external oblique")),
    ("erector_spinae", "muscular", 4000, muscle(
        "iliocostalis( cervicis| thoracis| lumborum)?",
        "longissimus( capitis| cervicis| thoracis)?", "spinalis( thoracis)?")),
    ("iliopsoas", "muscular", BIG_MUSCLE, muscle("psoas major", "iliacus")),

    # hip / thigh
    ("gluteus_maximus", "muscular", BIG_MUSCLE, muscle("gluteus maximus")),
    ("gluteus_medius", "muscular", MUSCLE, muscle("gluteus medius")),
    ("gluteus_minimus", "muscular", MUSCLE, muscle("gluteus minimus")),
    ("piriformis", "muscular", MUSCLE, muscle("piriformis")),
    ("tensor_fasciae_latae", "muscular", MUSCLE, muscle("tensor fasciae latae")),
    ("sartorius", "muscular", MUSCLE, muscle("sartorius")),
    ("rectus_femoris", "muscular", MUSCLE, muscle("rectus femoris")),
    ("vastus_lateralis", "muscular", MUSCLE, muscle("vastus lateralis")),
    ("vastus_medialis", "muscular", MUSCLE, muscle("vastus medialis")),
    ("vastus_intermedius", "muscular", MUSCLE, muscle("vastus intermedius")),
    ("adductors", "muscular", 3000, muscle(
        "adductor longus", "adductor brevis", "adductor magnus", "adductor minimus")),
    ("gracilis", "muscular", MUSCLE, muscle("gracilis")),
    ("biceps_femoris", "muscular", MUSCLE, muscle("biceps femoris")),
    ("semitendinosus", "muscular", MUSCLE, muscle("semitendinosus")),
    ("semimembranosus", "muscular", MUSCLE, muscle("semimembranosus")),

    # leg
    ("gastrocnemius", "muscular", BIG_MUSCLE, muscle("gastrocnemius")),
    ("soleus", "muscular", MUSCLE, muscle("soleus")),
    ("tibialis_anterior", "muscular", MUSCLE, muscle("tibialis anterior")),
    ("fibularis", "muscular", MUSCLE, muscle("fibularis longus", "fibularis brevis")),
]

# Source elements that are never drawn, with the reason. These are filed
# under the wrong concept in BodyParts3D 4.0.
BAD_ELEMENTS = {
    # Labelled "right anterior segmental artery" (lung, FMA8620) but they sit
    # in the right renal hilum, ~24 cm below that artery's other branches:
    # the missing anterior segmental branches of the right renal artery.
    "FJ2041": "renal artery branch filed under right lung",
    "FJ2044": "renal artery branch filed under right lung",
}

CONTEXT = [
    ("skull_other", "skeletal", 4000, ["skull"]),
    ("skin", "integumentary", 12000, ["skin"]),
]

# The female body: the BodyParts3D male with its pelvis swapped for the HRA
# (Human Reference Atlas) female one, plus female organs. Each entry is
# (id, system, budget, region, [(glb file, node regex), ...]); `region`
# names the transform in hra_transforms.json (see fit_hra.py). An id that is
# also a TARGET replaces that part in the female body, so questions about it
# work for both. The coccyx, which BodyParts3D lacks, is the HRA one here and
# Z-Anatomy's in the male body (see ZANATOMY_TARGETS).
HRA_TARGETS = [
    ("hip_bone", "skeletal", 3000, "pelvis", [("pelvis-female", "(ilium|ischium|pubis)_compact")]),
    ("sacrum", "skeletal", BIG_BONE, "pelvis", [("pelvis-female", "sacrum$")]),
    ("coccyx", "skeletal", SMALL_BONE, "pelvis", [("pelvis-female", "coccyx$")]),
    ("uterus", "reproductive", 3000, "pelvis", [("uterus-female", "")]),
    ("ovary", "reproductive", 800, "pelvis",
     [("ovary-female-left", ""), ("ovary-female-right", "")]),
    ("fallopian_tube", "reproductive", 1500, "pelvis",
     [("fallopian-tube-female-left", ""), ("fallopian-tube-female-right", "")]),
    # Outer surface only; lobes, ducts and ligaments sit hidden inside the fat.
    ("breast", "reproductive", 6000, "thorax",
     [("mammary-gland-female-left", "fat|areola|nipple"),
      ("mammary-gland-female-right", "fat|areola|nipple")]),
]

# Structures BodyParts3D lacks, from Z-Anatomy (CC BY-SA 4.0), which built
# them around its copy of the BodyParts3D skeleton. Each entry is
# (id, system, budget, [(Z-Anatomy object, region[, min_y]), ...]); `region`
# names a transform in zanatomy_transforms.json (see fit_zanatomy.py) and
# `min_y` (metres, body space) drops the triangles wholly below it. An id
# that is also a TARGET adds to that part. Shared by both bodies, except ids
# that HRA_TARGETS also has, which are male-only (the coccyx).
#
# BodyParts3D's common carotid ends at C6 and its internal carotid starts
# 6 cm higher, with nothing between, and Z-Anatomy's internal carotid takes
# a path ~14 mm away from ours. So the carotid tree comes from Z-Anatomy
# from the bifurcation up: the top of its common carotid bridges the gap
# from ours, and its internal carotid (which meets our cerebral arteries)
# replaces ours. Neck and face vessels use "head_neck", which blends the
# neck fit into the skull fit (the two heads are tilted ~6 degrees apart).
def za_pair(name, region):
    """A Z-Anatomy object's left and right copies (".l", ".r")."""
    return [(f"{name}.{side}", region) for side in "lr"]


ZANATOMY_TARGETS = [
    ("common_carotid", "cardiovascular", 300,
     [("Left common carotid artery", "head_neck", 1.365),
      ("Right common carotid artery", "head_neck", 1.365)]),
    ("internal_carotid", "cardiovascular", ARTERY,
     za_pair("Internal carotid artery", "head_neck")),
    ("external_carotid", "cardiovascular", ARTERY,
     za_pair("External carotid artery", "head_neck")),
    ("facial_artery", "cardiovascular", ARTERY,
     za_pair("Facial artery", "head_neck")),
    # The transverse facial artery is a branch of the superficial temporal.
    ("superficial_temporal_artery", "cardiovascular", ARTERY,
     [(f"{name}.{side}", "head_neck") for side in "lr" for name in (
         "Superficial temporal artery", "Frontal branch of superficial temporal artery",
         "Transverse facial artery")]),
    ("maxillary_artery", "cardiovascular", ARTERY,
     za_pair("Maxillary artery", "head_neck")),
    ("occipital_artery", "cardiovascular", ARTERY,
     za_pair("Occipital artery", "head_neck")),
    ("fibular_artery", "cardiovascular", ARTERY,
     [("Fibular artery.l", "leg_left"), ("Fibular artery.r", "leg_right")]),
    ("external_jugular_vein", "cardiovascular", ARTERY,
     za_pair("External jugular vein", "head_neck")),

    # Our lungs are only airway and vessel trees; Z-Anatomy's lobes give them
    # a surface. Z-Anatomy draws the cord as a cross-section arrayed along a
    # curve; Blender evaluates it into a tube.
    ("lungs", "respiratory", 6000,
     [(f"{lobe} lobe of {side} lung", "thorax")
      for side, lobes in (("right", ("Superior", "Middle", "Inferior")),
                          ("left", ("Superior", "Inferior")))
      for lobe in lobes]),
    ("spinal_cord", "nervous", 2000, [("White matter of spinal cord", "spine")]),
    # BodyParts3D's sacrum takes in the coccyx: see ZANATOMY_CARVE.
    ("coccyx", "skeletal", SMALL_BONE, [("Coccyx", "trunk")]),
    ("thyroid_gland", "endocrine", 1000, [("Thyroid gland", "neck")]),

    ("latissimus_dorsi", "muscular", BIG_MUSCLE, za_pair("Latissimus dorsi muscle", "trunk")),
    ("rectus_abdominis", "muscular", BIG_MUSCLE, za_pair("Rectus abdominis muscle", "trunk")),
    ("internal_oblique", "muscular", BIG_MUSCLE,
     za_pair("Internal abdominal oblique muscle", "trunk")),
    ("transversus_abdominis", "muscular", BIG_MUSCLE,
     za_pair("Transversus abdominis muscle", "trunk")),
    ("masseter", "muscular", MUSCLE,
     za_pair("Superficial part of masseter", "head") + za_pair("Deep part of masseter", "head")),
    ("temporalis", "muscular", MUSCLE, za_pair("Temporalis muscle", "head")),
    ("occipitofrontalis", "muscular", MUSCLE,
     za_pair("Frontalis muscle", "head") + za_pair("Occipitalis muscle", "head")),
    ("orbicularis_oculi", "muscular", MUSCLE,
     za_pair("Orbital part of orbicularis oculi", "head")
     + za_pair("Palpebral part of orbicularis oculi", "head")),
    ("orbicularis_oris", "muscular", MUSCLE, za_pair("Orbicularis oris muscle", "head")),
    ("zygomaticus_major", "muscular", MUSCLE, za_pair("Zygomaticus major muscle", "head")),
    ("platysma", "muscular", MUSCLE, za_pair("Platysma", "head_neck")),
]

# Z-Anatomy parts a BodyParts3D part already includes: {id: (part, metres)}.
# The part loses its faces lying wholly within that distance of the Z-Anatomy
# mesh, which covers the cut. BodyParts3D's sacrum runs on into the coccyx.
ZANATOMY_CARVE = {"coccyx": ("sacrum", 0.006)}

# Fit regions: (Z-Anatomy bone objects, the matching BodyParts3D selectors).
CERVICAL = [f"C{i}" for i in range(3, 8)]
THORACIC = [f"T{i}" for i in range(1, 13)]
LUMBAR = [f"L{i}" for i in range(1, 6)]
STERNUM = ["Manubrium of sternum", "Body of sternum"]
ORDINALS = ("First Second Third Fourth Fifth Sixth Seventh Eighth Ninth Tenth "
            "Eleventh Twelfth").split()


def za_ribs(numbers):
    return [f"{ORDINALS[n - 1]} rib.{side}" for n in numbers for side in "lr"]


ZANATOMY_FIT = {
    "neck": ([f"Intervertebral disc C{i}-{j}" for i, j in
              ((2, "C3"), (3, "C4"), (4, "C5"), (5, "C6"), (6, "C7"), (7, "T1"))]
             + ["Atlas (C1)", "Axis (C2)", "Hyoid bone"],
             ["re:^intervertebral disk of (axis|(third|fourth|fifth|sixth|seventh) "
              "cervical vertebra)$", "re:^atlas$", "re:^axis$", "hyoid bone"]),
    "head": (["Mandible", "Occipital bone", "Frontal bone"],
             ["mandible", "occipital bone", "frontal bone"]),
    "spine": (["Atlas (C1)", "Axis (C2)"] + [f"Vertebra {v}" for v in CERVICAL + THORACIC + LUMBAR],
              ["re:^atlas$", "re:^axis$", "re:^(third|fourth|fifth|sixth|seventh) cervical vertebra$",
               "re:^[a-z]+ (thoracic|lumbar) vertebra$"]),
    "thorax": (za_ribs(range(1, 13)) + STERNUM + [f"Vertebra {v}" for v in THORACIC],
               ["re:^(left|right) [a-z]+ rib$", "manubrium", "body of sternum",
                "re:^[a-z]+ thoracic vertebra$"]),
    "trunk": (za_ribs(range(1, 13)) + STERNUM + [f"Vertebra {v}" for v in THORACIC + LUMBAR]
              + ["Hip bone.l", "Hip bone.r", "Sacrum"],
              ["re:^(left|right) [a-z]+ rib$", "manubrium", "body of sternum",
               "re:^[a-z]+ (thoracic|lumbar) vertebra$", "re:^(left|right) hip bone$", "sacrum"]),
    "leg_left": (["Tibia.l", "Fibula.l"], ["re:^left (tibia|fibula)$"]),
    "leg_right": (["Tibia.r", "Fibula.r"], ["re:^right (tibia|fibula)$"]),
}

# Blended regions: (lower fit, upper fit, Z-Anatomy object, object). Points
# below the first object's mean height use the lower fit, above the second's
# the upper one, linearly mixed between.
ZANATOMY_BLENDS = {"head_neck": ("neck", "head", "Hyoid bone", "Atlas (C1)")}

# Parts only the male body has. TARGETS that HRA_TARGETS replace are male too.
# The BodyParts3D skin is the male outline; the female body gets its own
# (female_skin.npz, see fit_anny.py).
MALE_ONLY = {"prostate", "testis", "skin"}
