# WildSonic Live MCU Detection Test Report

- **Execution Time**: 2026-11-19T09:39:28.613424+00:00
- **Species Tested**: 126
- **Total Audio Plays**: 126
- **Assert Interruptions**: 0

## Overall Detection Accuracy

| Metric                          |    Count | Percentage |
| :------------------------------ | -------: | ---------: |
| **Top-1 Hits**                  | 41 / 126 |  **32.5%** |
| **Top-2 Hits (Top-1 or Top-2)** | 56 / 126 |  **44.4%** |
| **Misses**                      | 70 / 126 |      55.6% |
| **Short / No-Eval Windows**     |  0 / 126 |       0.0% |

## Silence Interval Analysis (False Positive Rejection)

| Metric                                 |     Value |
| :------------------------------------- | --------: |
| Total Silence Windows Evaluated        |        58 |
| Correct Background Rejections (id=126) |        43 |
| False Positive Bird Detections         |        15 |
| **Silence False Positive Rate**        | **25.9%** |

## Audio Staging & Queue Health

- **Max OCM Staging Ring High-Water Mark**: 17 / 18 blocks
- **Staging Lost / Overflow Samples**: 0 samples
- **Assert Events**: 0

## Per-Species Performance Summary

| Class ID | Species Name              | Plays | Eval Windows | Top-1 Hits | Top-2 Only | Misses | Top-1 Acc | Top-2 Acc |
| :------: | :------------------------ | :---: | :----------: | :--------: | :--------: | :----: | --------: | --------: |
|    0     | Alexandrine Parakeet      |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    1     | Ashy Drongo               |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    2     | Ashy Prinia               |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    3     | Asian Fairy-bluebird      |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    4     | Asian Koel                |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    5     | Barn Swallow              |   1   |      12      |     0      |     0      |   1    |      0.0% |      0.0% |
|    6     | Baya Weaver               |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    7     | Black Francolin           |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    8     | Black Kite                |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    9     | Black Redstart            |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    10    | Black-crowned Night-Heron |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    11    | Black-winged Kite         |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    12    | Black-winged Stilt        |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    13    | Blue-cheeked Bee-eater    |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    14    | Blue-tailed Bee-eater     |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    15    | Booted Warbler            |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    16    | Brahminy Kite             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    17    | Bronze-winged Jacana      |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    18    | Brown Boobook             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    19    | Brown-headed Barbet       |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    20    | Citrine Wagtail           |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    21    | Clamorous Reed Warbler    |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    22    | Common Chiffchaff         |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    23    | Common hawk-cuckoo        |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    24    | Common Kingfisher         |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    25    | Common Redshank           |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    26    | Common Sandpiper          |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    27    | Common Snipe              |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    28    | Common Tailorbird         |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    29    | Coppersmith Barbet        |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    30    | Crested Lark              |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    31    | Crested Serpent-Eagle     |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    32    | Crimson-backed Sunbird    |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    33    | Eastern Barn Owl          |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    34    | Eurasian Collared-Dove    |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    35    | Eurasian Coot             |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    36    | Eurasian Hoopoe           |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    37    | Eurasian Moorhen          |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    38    | Eurasian Wryneck          |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    39    | European Roller           |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    40    | Flame-throated Bulbul     |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    41    | Golden-fronted Leafbird   |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    42    | Gray Heron                |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    43    | Gray Wagtail              |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    44    | Gray-headed Bulbul        |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    45    | Great Cormorant           |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    46    | Greater Coucal            |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    47    | Green Bee-eater           |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    48    | Green Sandpiper           |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    49    | Green Warbler             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    50    | Greenish Warbler          |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    51    | House Crow                |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    52    | House Sparrow             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    53    | Indian Gray Hornbill      |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    54    | Indian Nightjar           |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    55    | Indian Peafowl            |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    56    | Indian Robin              |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    57    | Indian Roller             |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    58    | Indian Scops-Owl          |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    59    | Indian Silverbill         |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    60    | Indian White-eye          |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    61    | Jacobin Cuckoo            |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    62    | Jerdon's Nightjar         |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    63    | Jungle Babbler            |   1   |      2       |     0      |     1      |   0    |      0.0% |    100.0% |
|    64    | Large-billed Crow         |   1   |      0       |     0      |     1      |   0    |      0.0% |    100.0% |
|    65    | Large-billed Leaf Warbler |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    66    | Laughing Dove             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    67    | Lesser Coucal             |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    68    | Little Egret              |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    69    | Little Grebe              |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    70    | Little Spiderhunter       |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    71    | Little Stint              |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    72    | Little Swift              |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    73    | Long-billed Pipit         |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    74    | Malabar Barbet            |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    75    | Malabar Gray Hornbill     |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    76    | Malabar Imperial-Pigeon   |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    77    | Malabar Parakeet          |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    78    | Malabar Trogon            |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    79    | Malabar Whistling-Thrush  |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    80    | Marsh Sandpiper           |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    81    | Oriental Honey-buzzard    |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    82    | Paddyfield Pipit          |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|    83    | Painted Stork             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    84    | Pale-billed Flowerpecker  |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    85    | Peregrine Falcon          |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    86    | Pied Bushchat             |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    87    | Plain Prinia              |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    88    | Puff-throated Babbler     |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    89    | Purple Sunbird            |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    90    | Purple-rumped Sunbird     |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    91    | Red-rumped Swallow        |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    92    | Red-vented Bulbul         |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    93    | Red-wattled Lapwing       |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    94    | Red-whiskered Bulbul      |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|    95    | River Lapwing             |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|    96    | Rock Pigeon               |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|    97    | Rose-ringed Parakeet      |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    98    | Ruddy Shelduck            |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|    99    | Rufous Treepie            |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   100    | Rufous Woodpecker         |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|   101    | Scaly-breasted Munia      |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   102    | Shikra                    |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   103    | Southern Hill Myna        |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|   104    | Spotted dove              |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|   105    | Spotted Owlet             |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   106    | Tickell's Blue Flycatcher |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   107    | Tree Pipit                |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|   108    | Verditer Flycatcher       |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|   109    | Vernal Hanging-Parrot     |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   110    | Western Yellow Wagtail    |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|   111    | White Wagtail             |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|   112    | White-bellied Woodpecker  |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|   113    | White-breasted Waterhen   |   1   |      2       |     1      |     0      |   0    |    100.0% |    100.0% |
|   114    | White-browed Wagtail      |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|   115    | White-cheeked Barbet      |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   116    | White-throated Kingfisher |   1   |      0       |     1      |     0      |   0    |    100.0% |    100.0% |
|   117    | Wire-tailed Swallow       |   1   |      2       |     0      |     1      |   0    |      0.0% |    100.0% |
|   118    | Wood Sandpiper            |   1   |      2       |     0      |     0      |   1    |      0.0% |      0.0% |
|   119    | Yellow-bellied Prinia     |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|   120    | Yellow-browed Bulbul      |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   121    | Yellow-browed Warbler     |   1   |      1       |     1      |     0      |   0    |    100.0% |    100.0% |
|   122    | Yellow-eyed Babbler       |   1   |      1       |     0      |     1      |   0    |      0.0% |    100.0% |
|   123    | Yellow-throated Sparrow   |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   124    | Yellow-wattled Lapwing    |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
|   125    | Zitting Cisticola         |   1   |      1       |     0      |     0      |   1    |      0.0% |      0.0% |
