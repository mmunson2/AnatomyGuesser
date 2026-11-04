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
# work for both. The HRA coccyx is left out: BodyParts3D has none.
HRA_TARGETS = [
    ("hip_bone", "skeletal", 3000, "pelvis", [("pelvis-female", "(ilium|ischium|pubis)_compact")]),
    ("sacrum", "skeletal", BIG_BONE, "pelvis", [("pelvis-female", "sacrum$")]),
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

# Parts only the male body has. TARGETS that HRA_TARGETS replace are male too.
# The BodyParts3D skin is the male outline; the female body gets its own
# (female_skin.npz, see fit_anny.py).
MALE_ONLY = {"prostate", "testis", "skin"}
