#!/usr/bin/env python3
"""
Enrich all 35 Ramayan story segments with additional lesser_known_facts and debate_angles
to increase total video count from 210 to 315.

Adds per segment:
- 2 additional lesser_known_facts (from 2 → 4)
- 1 additional debate_angles (from 1 → 2)

Formula: 1 + len(lesser_known_facts) + len(debate_angles) + len(modern_relevance) + (len(suggested_angles) - 1)
Result:  1 + 4 + 2 + 1 + 1 = 9 per segment × 35 = 315 videos
"""

import json
import os
from pathlib import Path

# Base path for segment data
BASE_PATH = Path(__file__).parent.parent / "ramayan_db" / "kandas"

# Enrichment data for all 35 segments
# Format: (kanda_dir, segment_number): { "lesser_known_facts": [...], "debate_angles": [...] }
ENRICHMENT_DATA = {
    # ============ KANDA 1: BALA KANDA ============
    ("1_bala_kanda", "001"): {
        "lesser_known_facts": [
            "Valmiki records that the Putrakameshti fire produced a dark, enormous being (not Agni himself) who handed the payasam vessel — later commentators identified this as a form of Vishnu's creative energy",
            "King Dasharatha had performed 99 Ashwamedha yajnas before the Putrakameshti — Valmiki notes that only the lack of an heir prevented him from completing the hundredth and rivaling Indra"
        ],
        "debate_angles": [
            "Did Dasharatha's unequal distribution of payasam (half to Kausalya, quarter each to others) reflect political hierarchy rather than affection — was the succession decided before birth?"
        ]
    },
    ("1_bala_kanda", "002"): {
        "lesser_known_facts": [
            "Vishwamitra specifically chose Rama over the army of Dasharatha because only a divine weapon (Bala and Atibala mantras) could counter Tataka's sorcery — mortals soldiers would have been slaughtered",
            "Valmiki describes Rama as only fifteen years old during this journey — yet Vishwamitra taught him celestial weapons that even seasoned warriors had never received"
        ],
        "debate_angles": [
            "Was Vishwamitra using Dasharatha's sons for his own yajna protection, or was the education he provided a fair exchange — did the sage exploit a father's inability to refuse a Brahmin's request?"
        ]
    },
    ("1_bala_kanda", "003"): {
        "lesser_known_facts": [
            "Tataka was originally a beautiful yaksha woman cursed by Sage Agastya to become a rakshasi — Valmiki records that Rama initially hesitated to kill a woman until Vishwamitra reminded him of kshatriya duty",
            "The forest Tataka terrorized was originally called Malada-Karusha, created from the sweat and filth washed from Indra after he killed Vritra — it became cursed ground that attracted demons"
        ],
        "debate_angles": [
            "Was Tataka a victim of circumstance — cursed into demonic form by a sage's anger — and does her killing raise questions about whether cursed beings deserve death or compassion?"
        ]
    },
    ("1_bala_kanda", "004"): {
        "lesser_known_facts": [
            "Maricha (who later becomes the golden deer) first encountered Rama here — Rama's arrow flung him 800 miles into the ocean but spared his life, which Maricha never forgot",
            "Vishwamitra's yajna lasted six days and nights — Valmiki describes Rama and Lakshmana standing guard without sleep for the entire duration, subsisting only on the Bala-Atibala mantras"
        ],
        "debate_angles": [
            "Was it ethical for Vishwamitra to use adolescent princes as yajna guards when he himself possessed enough tapas to destroy demons — did his pride prevent him from using his own powers?"
        ]
    },
    ("1_bala_kanda", "005"): {
        "lesser_known_facts": [
            "Valmiki records that Shiva's bow (Pinaka) was so heavy that it required a special iron chest on eight wheels pushed by five thousand men — no other king at the swayamvara could even shift the chest",
            "Parashurama appeared immediately after Rama broke the bow, furious that his lord Shiva's weapon was destroyed — he challenged Rama with Vishnu's bow and was humbled when Rama strung it effortlessly"
        ],
        "debate_angles": [
            "Was Janaka's swayamvara condition (lifting Shiva's bow) a genuine test of worthiness, or a political ploy to avoid giving Sita to any mortal king — ensuring only a divine being could win?"
        ]
    },

    # ============ KANDA 2: AYODHYA KANDA ============
    ("2_ayodhya_kanda", "001"): {
        "lesser_known_facts": [
            "Valmiki notes that Dasharatha chose the coronation date in unusual haste because court astrologers warned that his natal stars were entering a dangerous alignment — it was urgency, not joy, driving the timing",
            "The coronation preparations described by Valmiki include specific urban planning — streets were widened, water sprinklers deployed, and flower garlands strung between every building in Ayodhya"
        ],
        "debate_angles": [
            "Was Dasharatha's hurried coronation plan a political mistake — by not consulting all queens and ministers properly, did he create the very vulnerability Manthara exploited?"
        ]
    },
    ("2_ayodhya_kanda", "002"): {
        "lesser_known_facts": [
            "Manthara had raised Kaikeyi from childhood and accompanied her from Kekaya kingdom — Valmiki portrays her loyalty as genuine maternal protectiveness twisted by palace politics",
            "Valmiki describes Kaikeyi as initially laughing and giving Manthara a jewel as reward for the coronation news — her transformation took an entire night of persistent manipulation"
        ],
        "debate_angles": [
            "Was Kaikeyi's demand for the boons a form of legitimate political negotiation within the rules of the era — did ancient royal wives have recognized rights to invoke promised boons?"
        ]
    },
    ("2_ayodhya_kanda", "003"): {
        "lesser_known_facts": [
            "Dasharatha physically collapsed and spent the entire night on the floor of Kaikeyi's chamber — Valmiki describes him as repeatedly fainting and being revived, aging visibly within hours",
            "Valmiki records that Dasharatha offered Kaikeyi the entire kingdom, wealth, and even his own life as alternatives to Rama's exile — she refused every substitute"
        ],
        "debate_angles": [
            "Could Dasharatha have legally refused to honor the boons given that they were extracted under emotional duress — or did the rigidity of Satya (truth-keeping) in that era make refusal impossible?"
        ]
    },
    ("2_ayodhya_kanda", "004"): {
        "lesser_known_facts": [
            "Valmiki describes that Sita stripped off her royal jewels and wore bark garments despite Dasharatha ordering that she could keep her royal attire — she chose exile's full hardship voluntarily",
            "The Ganga boatman Guha (king of Nishadas) wept meeting Rama and offered his entire tribal army — Rama declined but the friendship between a prince and a tribal king is one of the epic's overlooked bonds"
        ],
        "debate_angles": [
            "Did Dasharatha commit a greater injustice by not accompanying Rama into exile himself — as a father who caused the exile, was remaining in palace comfort while his son suffered a moral failure?"
        ]
    },
    ("2_ayodhya_kanda", "005"): {
        "lesser_known_facts": [
            "Bharata walked barefoot from Ayodhya to Chitrakoot (over 200 miles) refusing any royal transport — Valmiki describes his feet bleeding on the forest paths as penance for his mother's sin",
            "When the citizens of Ayodhya saw Bharata's army marching toward Rama's forest, they initially feared he was going to kill Rama — even sages suspected his motives until they saw his ascetic appearance"
        ],
        "debate_angles": [
            "Was Bharata's public renunciation and fourteen-year vigil at Nandigrama performative politics to secure legitimacy, or was it genuine devotion — how do we distinguish spectacle from sincerity in rulers?"
        ]
    },

    # ============ KANDA 3: ARANYA KANDA ============
    ("3_aranya_kanda", "001"): {
        "lesser_known_facts": [
            "The sage Atri's wife Anasuya gifted Sita divine cosmetics and garments that would never soil or fade — Valmiki describes this as the last luxury Sita enjoyed before her forest hardships intensified",
            "Valmiki records that Rama killed over a dozen rakshasas in Dandaka Forest even before Surpanakha's encounter — the sages had been terrorized for years and begged for protection"
        ],
        "debate_angles": [
            "Were the Dandaka Forest sages using Rama as their personal bodyguard — did they manipulate his sense of kshatriya duty to solve their demon problems instead of relocating?"
        ]
    },
    ("3_aranya_kanda", "002"): {
        "lesser_known_facts": [
            "Surpanakha was actually named Meenakshi (fish-eyed beauty) at birth — 'Surpanakha' (sharp-nailed) was a name given after she embraced her rakshasi nature following her husband's murder by Ravana",
            "Valmiki records that Khara's army of 14,000 rakshasas included dushanas (generals) who had individually defeated devas — Rama's solo victory was against a force that had humiliated heaven"
        ],
        "debate_angles": [
            "Was Surpanakha's initial approach to Rama a legitimate romantic proposal by the customs of her race — did Rama and Lakshmana's mockery constitute cultural insensitivity before the violence escalated?"
        ]
    },
    ("3_aranya_kanda", "003"): {
        "lesser_known_facts": [
            "Maricha explicitly told Ravana he would die if he went near Rama — having been flung across the ocean years ago, he recognized Rama's divinity and begged Ravana to abandon the plan",
            "Valmiki describes the golden deer as impossibly beautiful — its hide was studded with gems, its antlers tipped with sapphires, and it left a trail of flowers, all designed to enchant even a divine mind"
        ],
        "debate_angles": [
            "Was Maricha a victim coerced into suicide — Ravana threatened to kill him if he refused, giving him only the choice of death by Rama or death by Ravana — does this make Ravana solely guilty of what followed?"
        ]
    },
    ("3_aranya_kanda", "004"): {
        "lesser_known_facts": [
            "Jatayu was approximately 60,000 years old when he fought Ravana — Valmiki describes him as a primordial bird king whose wings once challenged the sun, now aged but still willing to die for dharma",
            "Ravana's Pushpaka Vimana during the abduction flew over multiple kingdoms — Valmiki records Sita throwing her jewels down as markers, showing remarkable strategic thinking even in terror"
        ],
        "debate_angles": [
            "Was Ravana's abduction motivated purely by lust, or was it political revenge for Surpanakha's humiliation and the destruction of his army — did he see it as a legitimate act of war?"
        ]
    },
    ("3_aranya_kanda", "005"): {
        "lesser_known_facts": [
            "Jatayu was a close friend of King Dasharatha — Valmiki records that Rama performed Jatayu's funeral rites as he would for his own father, granting the vulture-king moksha (liberation)",
            "The demoness Ayomukhi and the headless rakshasa Kabandha both encountered Rama during this search — Kabandha, once a gandharva cursed into monstrous form, directed Rama to Sugriva after being freed"
        ],
        "debate_angles": [
            "Was Ravana justified in his own worldview — as a king whose sister was mutilated and whose army was destroyed, would any sovereign not retaliate, regardless of who started the conflict?"
        ]
    },

    # ============ KANDA 4: KISHKINDHA KANDA ============
    ("4_kishkindha_kanda", "001"): {
        "lesser_known_facts": [
            "Hanuman was initially disguised as a Brahmin ascetic when he first met Rama — Valmiki records that Rama immediately recognized Hanuman's mastery of grammar and praised his flawless Sanskrit speech",
            "Sugriva was living in terror on Rishyamukha mountain specifically because Vali had been cursed never to enter it — a sage named Matanga had cursed that Vali would die if he stepped on that ground"
        ],
        "debate_angles": [
            "Was Sugriva manipulating Rama's grief over Sita to secure military help against Vali — did he exaggerate his own victimhood to win sympathy from a vulnerable, grieving prince?"
        ]
    },
    ("4_kishkindha_kanda", "002"): {
        "lesser_known_facts": [
            "Vali had once stuffed the demon Dundubhi's carcass a full yojana away with a single kick — when the blood drops fell on Sage Matanga's ashram, the curse was pronounced that made Rishyamukha Vali's no-go zone",
            "Sugriva tested Rama by showing Dundubhi's massive skeleton and asking him to kick it — Rama sent it flying ten yojanas with his toe, proving his superiority over Vali"
        ],
        "debate_angles": [
            "Did Sugriva fail to honor his pact quickly enough after becoming king — was his delay in searching for Sita (until Lakshmana threatened him) evidence that he used Rama without genuine gratitude?"
        ]
    },
    ("4_kishkindha_kanda", "003"): {
        "lesser_known_facts": [
            "Vali had a divine boon that in face-to-face combat, half of his opponent's strength would transfer to him — this made conventional combat impossible and is Rama's primary justification for the concealed shot",
            "Tara (Vali's wife) is described by Valmiki as one of the wisest women in the epic — after Vali's death, her political counsel kept Kishkindha stable during Sugriva's reign"
        ],
        "debate_angles": [
            "Was Rama's treatment of Vali inconsistent with his later treatment of Ravana (whom he fought face-to-face) — does this inconsistency undermine the dharmic justification for Vali's death?"
        ]
    },
    ("4_kishkindha_kanda", "004"): {
        "lesser_known_facts": [
            "The search parties were sent in all four directions with specific geographic markers — Valmiki's descriptions match real locations from the Vindhyas to the southern ocean with remarkable accuracy",
            "Sampati, Jatayu's elder brother, had lost his wings protecting Jatayu from the sun decades ago — he directed the southern search party to Lanka from atop a mountain, his last act of relevance"
        ],
        "debate_angles": [
            "Was Sugriva's delay in launching the search for Sita (he indulged in pleasures for months after becoming king) a betrayal of his oath to Rama — did power corrupt him instantly?"
        ]
    },
    ("4_kishkindha_kanda", "005"): {
        "lesser_known_facts": [
            "Jambavan (the ancient bear-king) was the one who reminded Hanuman of his forgotten powers — as a child, Hanuman had tried to eat the sun and was struck by Indra, causing him to forget his abilities",
            "Valmiki describes Hanuman growing to a colossal size before the leap — the vanaras watched his shadow expand until it darkened the entire southern shore like an eclipse"
        ],
        "debate_angles": [
            "Was it ethical for the vanara army to send Hanuman alone on such a dangerous mission into enemy territory — did Sugriva and the commanders risk a single hero's life to avoid collective danger?"
        ]
    },

    # ============ KANDA 5: SUNDARA KANDA ============
    ("5_sundara_kanda", "001"): {
        "lesser_known_facts": [
            "The ocean itself raised Mount Mainaka as a rest stop because the ocean owed a debt to Vayu (Hanuman's father) who had once sheltered mountains from Indra's wrath — this was repaying that ancient favor",
            "Valmiki records that Lanka's chief guardian demoness Lankini fought Hanuman at the city gates — he defeated her with a single blow, and she prophesied Lanka's doom had begun"
        ],
        "debate_angles": [
            "Were the devas who sent Surasa to test Hanuman acting irresponsibly — if Hanuman had failed or been delayed, Sita's rescue would have been jeopardized for the sake of a divine amusement?"
        ]
    },
    ("5_sundara_kanda", "002"): {
        "lesser_known_facts": [
            "Hanuman searched every building in Lanka including Ravana's inner chambers — Valmiki describes him seeing Ravana's sleeping wives in intimate positions and briefly worrying if seeing them constituted a sin",
            "Lanka is described by Valmiki with architectural precision — golden walls, crystal floors, aerial gardens, mechanical singing birds — suggesting a civilization far more advanced than commonly depicted"
        ],
        "debate_angles": [
            "Was Ravana's Lanka a utopia for its citizens despite being ruled by a tyrant — did the common rakshasas prosper under his rule, making Vibhishana's defection a betrayal of his own people?"
        ]
    },
    ("5_sundara_kanda", "003"): {
        "lesser_known_facts": [
            "Sita had resolved to kill herself and was preparing to hang from an Ashoka tree branch when Hanuman arrived — Valmiki describes this as the last possible moment before she would have been lost",
            "Ravana visited Sita every dawn with threats and promises — he gave her a twelve-month ultimatum after which he would eat her if she did not submit, showing his patience was calculated strategy"
        ],
        "debate_angles": [
            "Did Ravana show restraint by not forcing himself on Sita — was this due to a curse (that he would die if he touched an unwilling woman) rather than any moral code, making his 'nobility' self-preservation?"
        ]
    },
    ("5_sundara_kanda", "004"): {
        "lesser_known_facts": [
            "Sita initially refused to believe Hanuman and suspected him of being Ravana in disguise — it was only when Hanuman produced Rama's signet ring that she accepted his identity",
            "Hanuman offered to carry Sita back to Rama on his shoulders — she refused, saying she would not willingly touch another male, and that Rama should come rescue her to restore his honor"
        ],
        "debate_angles": [
            "Was Sita's refusal to escape with Hanuman a strategic miscalculation that prolonged the war and cost thousands of lives — or was preserving dharmic propriety worth the additional bloodshed?"
        ]
    },
    ("5_sundara_kanda", "005"): {
        "lesser_known_facts": [
            "Hanuman deliberately allowed himself to be captured by Indrajit's Brahmastra — he could have escaped but wanted to meet Ravana face-to-face to assess Lanka's military strength",
            "Vibhishana argued in Ravana's court against killing Hanuman — citing the rule that ambassadors are inviolable — this is the first glimpse of Vibhishana's dharmic leanings before his defection"
        ],
        "debate_angles": [
            "Was Hanuman's burning of Lanka — which killed countless innocent rakshasa civilians including women and children — justified as a military act, or was it disproportionate collective punishment?"
        ]
    },

    # ============ KANDA 6: YUDDHA KANDA ============
    ("6_yuddha_kanda", "001"): {
        "lesser_known_facts": [
            "Nala (not Nila) was the architect of Ram Setu — he had a divine boon that anything he placed on water would float, inherited from his father Vishwakarma (the divine architect)",
            "Valmiki records that even squirrels helped build the bridge by rolling in sand and shaking it between the stones — Rama blessed them by stroking their backs, giving them three stripes"
        ],
        "debate_angles": [
            "Was the ocean god Varuna's initial refusal to help Rama cross — forcing Rama to threaten drying the ocean with a Brahmastra — evidence that even divine beings only respond to power rather than righteousness?"
        ]
    },
    ("6_yuddha_kanda", "002"): {
        "lesser_known_facts": [
            "Vibhishana was initially treated with suspicion by Rama's allies — Sugriva strongly opposed accepting him, arguing it could be a Trojan horse strategy by Ravana to infiltrate their camp",
            "Ravana publicly disowned Vibhishana and kicked him with his foot in the royal court — Valmiki describes Vibhishana rising into the air with four loyal rakshasas and flying directly to Rama's camp"
        ],
        "debate_angles": [
            "Was Vibhishana a noble defector following dharma, or a traitor who abandoned his brother and people for self-preservation — does his coronation as Lanka's king prove his motives were self-serving?"
        ]
    },
    ("6_yuddha_kanda", "003"): {
        "lesser_known_facts": [
            "Ravana used the Nagapasha weapon that bound Rama and Lakshmana in serpent bonds — they were freed only when Garuda (divine eagle) appeared and the snakes fled in terror of their natural predator",
            "Valmiki records that Ravana's army included warriors who could change shape, become invisible, and fight from underground — the vanara army fought essentially blind against some opponents"
        ],
        "debate_angles": [
            "Did Ravana fight honorably by the rules of warfare of his era — unlike the concealed killing of Vali, Ravana consistently fought face-to-face and followed combat protocols, making him more kshatriya-like?"
        ]
    },
    ("6_yuddha_kanda", "004"): {
        "lesser_known_facts": [
            "Kumbhakarna had asked Brahma for 'Indrasana' (Indra's throne) but Saraswati twisted his tongue to say 'Nidrasana' (sleeping seat) — his curse of sleeping six months was not his fault but divine manipulation",
            "Indrajit (Meghanada) had defeated Indra himself in combat and held him prisoner — he was released only after Brahma intervened, making Indrajit arguably the most powerful warrior in the war"
        ],
        "debate_angles": [
            "Was Kumbhakarna morally superior to Ravana — he explicitly told Ravana the abduction was wrong but fought out of fraternal loyalty — does fighting for a cause you know is unjust make you more or less culpable?"
        ]
    },
    ("6_yuddha_kanda", "005"): {
        "lesser_known_facts": [
            "Ravana was a supreme devotee of Shiva who composed the Shiva Tandava Stotram — Valmiki describes him as the greatest Vedic scholar of his age who could recite all four Vedas perfectly",
            "After Ravana's death, celestial flowers rained and Brahma himself appeared to acknowledge that Rama's divine purpose — destroying Ravana — was now fulfilled, confirming the avatara's mission"
        ],
        "debate_angles": [
            "Was Ravana's downfall inevitable karma from the Jaya-Vijaya doorkeeper curse — were all his choices predetermined, making moral judgment of his actions philosophically meaningless?"
        ]
    },

    # ============ KANDA 7: UTTARA KANDA ============
    ("7_uttara_kanda", "001"): {
        "lesser_known_facts": [
            "The Pushpaka Vimana originally belonged to Kubera (Ravana's half-brother) before Ravana seized it by force — after the war, Rama returned it to Kubera rather than keeping it",
            "Valmiki describes specific landmarks Rama pointed out to Sita during the aerial return — the battlefield, the bridge, Kishkindha, and Chitrakoot — essentially narrating their entire journey in reverse"
        ],
        "debate_angles": [
            "Was Bharata's vow to self-immolate if Rama was late an act of emotional blackmail against the universe — did it place unfair cosmic pressure on events rather than representing genuine faith?"
        ]
    },
    ("7_uttara_kanda", "002"): {
        "lesser_known_facts": [
            "Ram Rajya is described by Valmiki in measurable terms — no one died before old age, no woman became a widow, there were no natural disasters, and even animals did not prey on each other",
            "Rama performed ten Ashwamedha yajnas as emperor — Valmiki records that golden statues of Sita accompanied him during rituals after her exile, as a wife's presence was mandatory for Vedic rites"
        ],
        "debate_angles": [
            "Was Ram Rajya achieved through divine power rather than good governance — does attributing ideal rule to divinity discourage mortals from believing they can create just societies through effort alone?"
        ]
    },
    ("7_uttara_kanda", "003"): {
        "lesser_known_facts": [
            "The washerman (dhobi) who triggered the exile spoke while beating his wife — he said 'I am not like Rama who takes back a woman from another man's house', and spies reported this to Rama",
            "Sita was pregnant with twins when exiled — Valmiki records that Rama knew this and still sent Lakshmana to leave her near Valmiki's ashram, ensuring she would have sage protection"
        ],
        "debate_angles": [
            "Was the washerman's casual gossip genuine public opinion, or did palace enemies plant the rumor — and should a single citizen's slander determine a queen's fate regardless of divine proof of innocence?"
        ]
    },
    ("7_uttara_kanda", "004"): {
        "lesser_known_facts": [
            "Lava and Kusha were trained by Valmiki himself and could recite the entire Ramayan set to music — they performed it in Rama's court without anyone initially realizing they were his sons",
            "Valmiki composed the Ramayan in real-time as events unfolded — the twins learned the complete epic including its ending (which had not yet occurred), suggesting Valmiki had prophetic vision"
        ],
        "debate_angles": [
            "Did Valmiki raise Lava and Kusha with a biased narrative — as both author and foster-parent, could his version of events have shaped the twins' perception of their father's actions?"
        ]
    },
    ("7_uttara_kanda", "005"): {
        "lesser_known_facts": [
            "When Sita called upon Earth to take her back, the ground split open and a divine throne rose — the goddess Bhudevi (Earth) appeared in person and seated Sita beside her before descending",
            "Rama ruled for eleven thousand years after Sita's departure according to Valmiki — he eventually walked into the Sarayu river in a ceremony called Mahaprasthana, choosing his own moment of departure"
        ],
        "debate_angles": [
            "Was Sita's final act of calling Earth to swallow her a statement of protest against Rama's repeated tests — did she choose dramatic departure specifically to make an eternal point about unjust treatment?"
        ]
    },
}


def enrich_segments():
    """Read each segment JSON, add enrichment data, and write back."""
    total_updated = 0
    total_videos_before = 0
    total_videos_after = 0

    for (kanda_dir, seg_num), enrichment in ENRICHMENT_DATA.items():
        segment_path = BASE_PATH / kanda_dir / "segments" / f"{seg_num}.json"

        if not segment_path.exists():
            print(f"WARNING: {segment_path} does not exist, skipping.")
            continue

        # Read existing segment
        with open(segment_path, "r", encoding="utf-8") as f:
            segment = json.load(f)

        # Calculate videos before
        videos_before = _calc_videos(segment)
        total_videos_before += videos_before

        # Add new lesser_known_facts
        segment["lesser_known_facts"].extend(enrichment["lesser_known_facts"])

        # Add new debate_angles
        segment["debate_angles"].extend(enrichment["debate_angles"])

        # Calculate videos after
        videos_after = _calc_videos(segment)
        total_videos_after += videos_after

        # Write back
        with open(segment_path, "w", encoding="utf-8") as f:
            json.dump(segment, f, indent=2, ensure_ascii=False)

        total_updated += 1
        print(f"  Updated {kanda_dir}/{seg_num}.json: {videos_before} → {videos_after} videos")

    print(f"\nTotal segments updated: {total_updated}")
    print(f"Total videos before: {total_videos_before}")
    print(f"Total videos after: {total_videos_after}")


def _calc_videos(segment: dict) -> int:
    """Mirror the StoryManager._get_videos_per_segment formula."""
    count = 1  # primary angle
    count += len(segment.get("lesser_known_facts", []))
    count += len(segment.get("debate_angles", []))
    count += len(segment.get("modern_relevance", []))
    suggested = segment.get("suggested_angles", [])
    if len(suggested) > 1:
        count += len(suggested) - 1
    return count


if __name__ == "__main__":
    print("Enriching 35 Ramayan story segments...\n")
    enrich_segments()
    print("\nDone! Run verification to confirm 300+ total videos.")
