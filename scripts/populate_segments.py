#!/usr/bin/env python3
"""
Populate all 35 Ramayan segment JSON files (7 Kandas x 5 segments each).
Overwrites existing Bala/Ayodhya Kanda segments and creates new ones for Kandas 3-7.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "ramayan_db", "kandas")

SEGMENTS = []

# ============================================================
# KANDA 1 - BALA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 1,
    "kanda_name": "Bala Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "The Birth of Rama",
    "content": (
        "In the magnificent kingdom of Ayodhya, King Dasharatha ruled with wisdom and valor, "
        "yet his heart carried the weight of having no heir. On the counsel of Sage Vasishtha, "
        "the king performed the Putrakameshti Yajna under the guidance of Sage Rishyashringa. "
        "From the sacred fire emerged Agni himself, bearing a golden vessel filled with divine "
        "payasam. Dasharatha distributed this celestial offering among his three queens. "
        "Queen Kausalya received half, Queen Sumitra received two portions, and Queen Kaikeyi "
        "received one portion. In due time, on the auspicious Navami of Chaitra month, Kausalya "
        "gave birth to Rama, the embodiment of Vishnu. Kaikeyi bore Bharata, and Sumitra "
        "delivered twins Lakshmana and Shatrughna. The heavens showered flowers, celestial "
        "drums sounded, and all of Ayodhya rejoiced. The four princes filled the palace with "
        "divine light, each destined for extraordinary purpose."
    ),
    "characters": ["King Dasharatha", "Queen Kausalya", "Queen Kaikeyi", "Queen Sumitra",
                   "Rama", "Bharata", "Lakshmana", "Shatrughna", "Sage Vasishtha",
                   "Sage Rishyashringa"],
    "key_events": [
        "Putrakameshti Yajna performed under Sage Rishyashringa",
        "Agni delivers divine payasam from the sacred fire",
        "Birth of four princes - Rama, Bharata, Lakshmana, Shatrughna"
    ],
    "philosophical_themes": ["divine leela", "dharma", "karma"],
    "lesser_known_facts": [
        "Sage Rishyashringa, not Vasishtha, actually conducted the Putrakameshti Yajna - he was brought specifically because his purity ensured the yajna's success",
        "Valmiki describes that Sumitra received two shares of payasam - one from Kausalya and one from Kaikeyi - which is why she bore twins"
    ],
    "debate_angles": [
        "Was Dasharatha's distribution of payasam among queens based purely on affection, or did it follow a dharmic protocol of succession?"
    ],
    "modern_relevance": [
        "The power of patience and faith - Dasharatha waited decades for children, teaching us that worthy outcomes require sustained devotion and trust in the process"
    ],
    "suggested_angles": ["unknown_facts", "hidden_meaning"]
})

SEGMENTS.append({
    "kanda_index": 1,
    "kanda_name": "Bala Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Education Under Sage Vishwamitra",
    "content": (
        "The great sage Vishwamitra arrived at Dasharatha's court seeking warriors to protect "
        "his sacred yajna from demons. Though the king offered his entire army, Vishwamitra "
        "insisted on young Rama and Lakshmana alone. Dasharatha's heart trembled at the thought "
        "of sending his beloved sons into danger, but Sage Vasishtha counseled him to trust "
        "Vishwamitra's wisdom. As the princes departed with the sage, their education began "
        "immediately. Vishwamitra bestowed upon them the Bala and Atibala mantras — divine "
        "knowledge that freed them from hunger, thirst, and fatigue. He taught them the science "
        "of celestial weapons, each mantra carrying the power of the devas themselves. The "
        "forest became their classroom, and the greatest Brahmarishi became their guru. This "
        "journey transformed two royal princes into warriors destined to protect dharma, "
        "demonstrating that true education comes not from comfort but from challenge."
    ),
    "characters": ["Rama", "Lakshmana", "Sage Vishwamitra", "King Dasharatha", "Sage Vasishtha"],
    "key_events": [
        "Vishwamitra arrives seeking Rama's help against demons",
        "Dasharatha reluctantly sends Rama and Lakshmana with the sage",
        "Vishwamitra teaches Bala and Atibala mantras and celestial weapons"
    ],
    "philosophical_themes": ["duty", "sacrifice", "devotion"],
    "lesser_known_facts": [
        "Vishwamitra taught Rama the Bala and Atibala mantras before any battle - these made the princes immune to hunger and fatigue, a detail often skipped in retellings",
        "Dasharatha actually fainted when asked to send Rama - Vasishtha had to revive him and convince him of Vishwamitra's divine purpose"
    ],
    "debate_angles": [
        "Was Dasharatha wrong to hesitate sending his sons with Vishwamitra, or was his fatherly instinct a valid concern over a sage's demand?"
    ],
    "modern_relevance": [
        "Letting children face challenges builds resilience - Dasharatha's dilemma mirrors modern parents who must balance protection with allowing growth through difficulty"
    ],
    "suggested_angles": ["life_lesson", "character_study"]
})

SEGMENTS.append({
    "kanda_index": 1,
    "kanda_name": "Bala Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "The Slaying of Tataka",
    "content": (
        "As Rama and Lakshmana journeyed deeper with Vishwamitra, they entered the cursed "
        "forest of Tataka — once a beautiful region turned desolate by the demoness's terror. "
        "Vishwamitra revealed that Tataka was originally a Yaksha woman cursed into demonic form, "
        "possessing the strength of a thousand elephants. When Rama hesitated to strike a female, "
        "Vishwamitra explained that protecting the innocent supersedes gender considerations when "
        "dealing with those who have abandoned all dharma. Rama drew his bow, and the forest "
        "trembled. Tataka charged with uprooted trees and boulders, but Rama's arrows found "
        "their mark with divine precision. With her death, the forest bloomed instantly — flowers "
        "appeared, streams flowed again, and birds sang. The devas showered celestial weapons "
        "upon Rama as reward. This was his first act of dharmic warfare, establishing the "
        "principle that duty sometimes demands difficult choices."
    ),
    "characters": ["Rama", "Lakshmana", "Sage Vishwamitra", "Tataka"],
    "key_events": [
        "Journey through the cursed forest of Tataka",
        "Rama slays the demoness Tataka after overcoming hesitation",
        "Devas bestow divine celestial weapons upon Rama"
    ],
    "philosophical_themes": ["dharma", "courage", "duty"],
    "lesser_known_facts": [
        "Tataka was originally a beautiful Yaksha woman named Tataka who was cursed by Sage Agastya — Valmiki provides her full backstory which shows she was not inherently evil",
        "After Tataka's death, Vishwamitra gave Rama an arsenal of divine weapons including the Brahmastra, not just one or two — the full list spans several shlokas"
    ],
    "debate_angles": [
        "Was it justified to kill Tataka who was cursed into her demonic form, or should Rama have sought to break her curse instead?"
    ],
    "modern_relevance": [
        "Sometimes doing the right thing requires overcoming personal discomfort — leaders must make hard decisions that serve the greater good even when emotionally difficult"
    ],
    "suggested_angles": ["debate", "why"]
})

SEGMENTS.append({
    "kanda_index": 1,
    "kanda_name": "Bala Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "Protection of the Sacred Yajna",
    "content": (
        "Vishwamitra began his six-day yajna at Siddhashrama, with Rama and Lakshmana standing "
        "guard day and night. The princes maintained unwavering vigilance, knowing the demons "
        "would strike at the yajna's culmination. On the sixth day, as Vishwamitra reached the "
        "most sacred mantras, the sky darkened. Maricha and Subahu descended with hordes of "
        "demons, raining blood and filth upon the sacrificial fire. Rama, calm as the ocean, "
        "unleashed the Manavastra which hurled Maricha hundreds of yojanas into the sea. Then "
        "with the Agneyastra, he struck Subahu dead. The remaining demons scattered in terror. "
        "The yajna concluded successfully, the sacred fire burning pure once more. Vishwamitra "
        "blessed Rama, declaring that the boy had fulfilled a purpose no army could accomplish. "
        "The sages of the forest emerged from hiding, their years of fear finally ended by "
        "two young princes who embodied dharmic protection."
    ),
    "characters": ["Rama", "Lakshmana", "Sage Vishwamitra", "Maricha", "Subahu"],
    "key_events": [
        "Rama and Lakshmana guard Vishwamitra's yajna for six days",
        "Maricha hurled into the ocean by the Manavastra",
        "Subahu slain and demons defeated, yajna completed successfully"
    ],
    "philosophical_themes": ["duty", "courage", "dharma"],
    "lesser_known_facts": [
        "Rama specifically chose NOT to kill Maricha — he used the Manavastra to fling him far away, showing mercy that would have consequences later in Aranya Kanda",
        "Valmiki describes the yajna lasting six days and nights with Rama standing guard without sleep — the Bala-Atibala mantras sustained him"
    ],
    "debate_angles": [
        "Should Rama have killed Maricha at Siddhashrama when he had the chance, rather than showing mercy that later enabled the golden deer deception?"
    ],
    "modern_relevance": [
        "Patient vigilance and strategic restraint are more powerful than aggression — knowing when NOT to use full force is a mark of true leadership"
    ],
    "suggested_angles": ["what_if", "hidden_meaning"]
})

SEGMENTS.append({
    "kanda_index": 1,
    "kanda_name": "Bala Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "The Swayamvara and Marriage to Sita",
    "content": (
        "Vishwamitra led the princes to Mithila, the kingdom of the learned King Janaka. There "
        "stood Shiva's celestial bow, Pinaka — so heavy that no mortal had ever strung it. "
        "Janaka had declared that whoever could lift and string the bow would win his daughter "
        "Sita's hand, born from the Earth herself during a sacred ploughing. Hundreds of kings "
        "had failed, unable to even move the divine weapon. When Rama approached the bow with "
        "quiet confidence, the assembly fell silent. He lifted it effortlessly with one hand, "
        "and as he bent it to string, the bow snapped with a thunderous crack that echoed "
        "across three worlds. Shiva himself felt the vibration. Sita placed the garland upon "
        "Rama, their eyes meeting in divine recognition. King Janaka wept with joy. A grand "
        "wedding followed — Sita wed Rama, Urmila wed Lakshmana, Mandavi wed Bharata, and "
        "Shrutakirti wed Shatrughna. Four divine unions sealed in dharma."
    ),
    "characters": ["Rama", "Sita", "King Janaka", "Sage Vishwamitra", "Lakshmana",
                   "Bharata", "Shatrughna"],
    "key_events": [
        "Rama lifts and breaks Lord Shiva's bow Pinaka at the Swayamvara",
        "Sita garlands Rama as her chosen husband",
        "Grand quadruple wedding of all four princes to Janaka's daughters"
    ],
    "philosophical_themes": ["divine leela", "love", "dharma"],
    "lesser_known_facts": [
        "The broken bow's sound was so powerful that Parashurama felt it and came furiously to confront whoever dared break Shiva's bow — leading to a tense standoff with Rama",
        "All four brothers married on the same day — Urmila, Mandavi, and Shrutakirti were Sita's cousins, not sisters as popularly believed"
    ],
    "debate_angles": [
        "Was King Janaka's condition of the bow test fair to Sita, or did it reduce her agency by making her a prize rather than allowing her choice?"
    ],
    "modern_relevance": [
        "True strength reveals itself quietly — Rama's calm confidence amid boastful kings teaches that genuine capability doesn't need loud proclamation"
    ],
    "suggested_angles": ["unknown_facts", "life_lesson"]
})

# ============================================================
# KANDA 2 - AYODHYA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 2,
    "kanda_name": "Ayodhya Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "Preparations for Rama's Coronation",
    "content": (
        "King Dasharatha, feeling the weight of age, decided to crown Rama as Yuvaraja. The "
        "entire kingdom of Ayodhya erupted in celebration. Streets were decorated with flowers "
        "and festive banners, merchants displayed their finest wares, and citizens sang praises "
        "of their beloved prince. Rama had won the hearts of all through his compassion, wisdom, "
        "and unwavering adherence to dharma. Sage Vasishtha began preparations for the grand "
        "ceremony, selecting the most auspicious date by celestial calculations. Sacred items "
        "were gathered — golden vessels, holy waters from sacred rivers, precious gems, and "
        "ritual materials. Rama was informed of his father's decision and accepted it with "
        "characteristic humility, neither showing pride nor excessive joy. He sought blessings "
        "from all elders and visited temples. The night before the coronation, Ayodhya glowed "
        "with a thousand lamps, unaware that fate had written a vastly different script for "
        "the morrow."
    ),
    "characters": ["Rama", "King Dasharatha", "Sage Vasishtha", "Queen Kausalya"],
    "key_events": [
        "Dasharatha announces Rama's coronation as Yuvaraja",
        "Ayodhya celebrates with grand preparations and decorations",
        "Rama accepts the news with humble grace and seeks blessings"
    ],
    "philosophical_themes": ["dharma", "duty", "renunciation"],
    "lesser_known_facts": [
        "Dasharatha specifically chose a day when Bharata was away in his maternal grandfather's kingdom — Valmiki suggests this was intentional to avoid any succession dispute",
        "Valmiki describes Rama spending the night before coronation in fasting and meditation with Sita — performing rituals of preparedness, not celebration"
    ],
    "debate_angles": [
        "Was Dasharatha wrong to schedule coronation while Bharata was away — was this a political maneuver or genuine coincidence?"
    ],
    "modern_relevance": [
        "Succession planning in organizations requires transparency and timing — Dasharatha's secretive urgency mirrors how rushed leadership transitions create conflict"
    ],
    "suggested_angles": ["what_if", "debate"]
})

SEGMENTS.append({
    "kanda_index": 2,
    "kanda_name": "Ayodhya Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Manthara's Poisonous Counsel",
    "content": (
        "While Ayodhya rejoiced, the hunchbacked maid Manthara watched from the palace terrace "
        "with growing alarm. She rushed to Queen Kaikeyi's chambers with calculated words. "
        "Manthara painted a terrifying picture — once Rama became king, Kaikeyi would become "
        "a servant to Kausalya, and Bharata would be marginalized forever. Kaikeyi initially "
        "dismissed her, praising Rama's virtues. But Manthara persisted through the night, "
        "weaving stories of royal families destroyed by succession conflicts, appealing to "
        "Kaikeyi's pride and maternal instinct. She reminded Kaikeyi of the two boons Dasharatha "
        "had promised after the battle where Kaikeyi saved his life. Slowly, like poison seeping "
        "into clear water, doubt took root. Kaikeyi's love transformed into fear, her trust "
        "into suspicion. By dawn, she had retreated to the anger chamber (kopa griha), "
        "lying on the bare floor with disheveled hair, ready to demand what Manthara had "
        "crafted — exile for Rama, throne for Bharata."
    ),
    "characters": ["Manthara", "Queen Kaikeyi", "Queen Kausalya"],
    "key_events": [
        "Manthara poisons Kaikeyi's mind with fears of marginalization",
        "Kaikeyi remembers Dasharatha's two unfulfilled boons",
        "Kaikeyi enters the anger chamber to confront Dasharatha"
    ],
    "philosophical_themes": ["karma", "dharma", "duty"],
    "lesser_known_facts": [
        "Valmiki describes Kaikeyi as genuinely loving Rama like her own son — she resisted Manthara for hours before finally succumbing, showing this was not instant hatred",
        "The 'kopa griha' (anger chamber) was an actual architectural feature in ancient palaces — a designated space where queens could express displeasure as a form of protest"
    ],
    "debate_angles": [
        "Was Manthara acting purely out of malice, or did she genuinely fear for Kaikeyi's and Bharata's future security in the royal hierarchy?"
    ],
    "modern_relevance": [
        "Toxic advisors can corrupt even good people — the influence of negative counsel in corporate politics and personal relationships mirrors Manthara's manipulation"
    ],
    "suggested_angles": ["character_study", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 2,
    "kanda_name": "Ayodhya Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "The Two Boons and Rama's Exile",
    "content": (
        "Dasharatha found Kaikeyi in the anger chamber and desperately sought to console her. "
        "Blinded by love, he swore to grant whatever she desired. Kaikeyi then demanded her "
        "two boons — Bharata's coronation and Rama's fourteen-year exile to Dandaka forest. "
        "The words struck Dasharatha like thunderbolts. He collapsed, begging her to reconsider, "
        "offering his life instead. But Kaikeyi held firm, invoking his honor and the sanctity "
        "of a Kshatriya's word. When Rama learned of the exile, he accepted it with absolute "
        "serenity. Not a shadow of anger crossed his face. He told his father that fourteen "
        "years would pass like a dream, and that dharma demanded obedience to a father's word "
        "regardless of circumstance. Rama's calm acceptance stunned the court. He prepared "
        "for forest life immediately, removing his royal garments and donning tree bark. "
        "In that moment, Rama demonstrated that true nobility lies not in receiving a crown "
        "but in how one bears loss."
    ),
    "characters": ["Rama", "King Dasharatha", "Queen Kaikeyi", "Sita", "Lakshmana"],
    "key_events": [
        "Kaikeyi demands Bharata's coronation and Rama's fourteen-year exile",
        "Dasharatha collapses in grief but cannot break his word",
        "Rama accepts exile with complete serenity and removes royal garments"
    ],
    "philosophical_themes": ["dharma", "sacrifice", "truth", "renunciation"],
    "lesser_known_facts": [
        "Valmiki records that Dasharatha offered to give up his kingdom and become Kaikeyi's slave — his pleas lasted through the entire night before Rama was informed",
        "Rama's bark garments were brought by Kaikeyi herself — when Sita struggled to wear them, Sage Vasishtha intervened and cursed that Kaikeyi's line would not inherit"
    ],
    "debate_angles": [
        "Was Kaikeyi's demand legally valid since the boons were promised in a war context, or was she exploiting a technicality from a different circumstance?"
    ],
    "modern_relevance": [
        "Integrity means honoring commitments even when costly — in an age of broken promises, Rama's acceptance shows that character is revealed not in easy times but in moments of injustice"
    ],
    "suggested_angles": ["why", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 2,
    "kanda_name": "Ayodhya Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "Departure to the Forest",
    "content": (
        "When Sita learned of the exile, she refused to remain in palace comfort while her "
        "husband suffered. She declared that a wife's place is beside her husband — forest or "
        "palace makes no difference. Rama tried dissuading her, describing the dangers of "
        "wild animals, harsh terrain, and deprivation. But Sita's resolve was absolute. "
        "Lakshmana too insisted on accompanying his brother, his fierce devotion brooking no "
        "argument. As the three departed on Sumantra's chariot, the citizens of Ayodhya "
        "followed them weeping, unwilling to let Rama go. The scene was heart-wrenching — "
        "elderly men, women, children, even animals seemed to mourn. Rama had to depart "
        "secretly at night to avoid the grieving crowds. At the banks of the Tamasa river, "
        "he looked back one final time at his sleeping people who had followed him even there. "
        "The princes crossed river after river — Ganga, Yamuna — meeting sages and hermits "
        "who guided their path into the Dandaka wilderness."
    ),
    "characters": ["Rama", "Sita", "Lakshmana", "Sumantra"],
    "key_events": [
        "Sita and Lakshmana insist on joining Rama in exile",
        "Citizens of Ayodhya follow Rama weeping, unable to let him go",
        "The trio departs secretly at night, crossing Tamasa, Ganga, and Yamuna rivers"
    ],
    "philosophical_themes": ["love", "devotion", "sacrifice", "duty"],
    "lesser_known_facts": [
        "Rama had to secretly leave at night because the citizens literally camped around his chariot refusing to return — he crossed the Tamasa river while they slept",
        "Sumantra the charioteer drove them to the forest border and wept so heavily upon returning that Dasharatha could not bear to hear his account"
    ],
    "debate_angles": [
        "Did Sumantra fail in his duty by not refusing the king's order, or was his obedience the only dharmic choice available to a servant?"
    ],
    "modern_relevance": [
        "True partnership means sharing hardship equally — Sita's insistence on joining Rama in exile teaches that love is proven not in comfort but in willingness to share suffering"
    ],
    "suggested_angles": ["life_lesson", "character_study"]
})

SEGMENTS.append({
    "kanda_index": 2,
    "kanda_name": "Ayodhya Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "Bharata's Return and Devotion",
    "content": (
        "King Dasharatha, unable to bear the separation from Rama, uttered his last words — "
        "'Rama... Rama...' — and departed from the mortal world. When Bharata returned from "
        "his grandfather's kingdom to find his father dead and Rama exiled, his grief was "
        "boundless. Learning of his mother Kaikeyi's role, he rebuked her with burning words, "
        "declaring he wanted no part of a throne stolen from his brother. Bharata led an "
        "entire army to the forest — not to claim kingship, but to beg Rama to return. At "
        "Chitrakoot, the brothers met in an emotional reunion. Bharata fell at Rama's feet, "
        "pleading him to return and rule. But Rama gently refused, insisting on fulfilling "
        "their father's word completely. In an act of supreme devotion, Bharata asked for "
        "Rama's sandals, which he placed upon the throne of Ayodhya. He ruled as Rama's "
        "regent from the village of Nandigrama, living as an ascetic, waiting fourteen years "
        "for his brother's return."
    ),
    "characters": ["Bharata", "Rama", "King Dasharatha", "Queen Kaikeyi", "Lakshmana", "Sita"],
    "key_events": [
        "Dasharatha dies of grief calling Rama's name",
        "Bharata rebukes Kaikeyi and refuses the throne",
        "Bharata places Rama's sandals on the throne and rules as regent from Nandigrama"
    ],
    "philosophical_themes": ["devotion", "dharma", "sacrifice", "love"],
    "lesser_known_facts": [
        "Bharata vowed to enter fire if Rama did not return after exactly fourteen years — he literally kept a fire ready in Nandigrama for this purpose",
        "Valmiki describes that Bharata lived outside the city in Nandigrama wearing matted hair and bark clothes like an ascetic, never once sitting on the throne"
    ],
    "debate_angles": [
        "Was Kaikeyi redeemable after seeing Bharata's rejection, or had she crossed a point of no return in dharmic terms?"
    ],
    "modern_relevance": [
        "Servant leadership exemplified — Bharata ruling only as a regent with sandals as authority shows that true power comes from representing others' trust, not personal ambition"
    ],
    "suggested_angles": ["character_study", "life_lesson"]
})

# ============================================================
# KANDA 3 - ARANYA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 3,
    "kanda_name": "Aranya Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "Life in the Dandaka Forest",
    "content": (
        "After traversing through the wilderness, Rama, Sita, and Lakshmana established their "
        "hermitage at Panchavati on the banks of the Godavari river, guided by the sage "
        "Agastya. The location was blessed with natural beauty — flowering trees, crystal "
        "streams, and abundant wildlife. Lakshmana built a beautiful cottage with his own "
        "hands, thatched with leaves and surrounded by fragrant gardens. Here the three "
        "lived in simplicity and contentment. Rama spent his days meeting forest sages who "
        "sought protection from rakshasas troubling their rituals. He promised each of them "
        "safety, becoming the guardian of the entire Dandaka forest. Sita transformed their "
        "simple hermitage into a home filled with warmth. The thirteen years of exile became "
        "a period of deep spiritual growth. They lived among nature, performing daily rituals, "
        "studying sacred texts, and finding that peace is not a place but a state of being. "
        "The forest life strengthened their bonds immeasurably."
    ),
    "characters": ["Rama", "Sita", "Lakshmana", "Sage Agastya"],
    "key_events": [
        "Hermitage established at Panchavati on the banks of Godavari",
        "Lakshmana builds a cottage with his own hands",
        "Rama promises protection to all forest sages from rakshasas"
    ],
    "philosophical_themes": ["renunciation", "devotion", "dharma"],
    "lesser_known_facts": [
        "Sage Agastya gave Rama the divine bow of Vishnu, an inexhaustible quiver, and a celestial sword before directing him to Panchavati — these weapons were crucial later",
        "Valmiki describes thirteen years passing peacefully at Panchavati — the dramatic events happened only in the final year of exile"
    ],
    "debate_angles": [
        "Was Sage Agastya directing Rama to Panchavati a strategic move knowing it would lead to confrontation with Ravana, or genuine advice for peaceful living?"
    ],
    "modern_relevance": [
        "Simplicity brings clarity — stripping away material excess, like Rama's forest life, teaches that purpose and peace come from relationships and duty, not possessions"
    ],
    "suggested_angles": ["hidden_meaning", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 3,
    "kanda_name": "Aranya Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Surpanakha's Encounter",
    "content": (
        "The peaceful days at Panchavati were shattered when Surpanakha, Ravana's sister, "
        "wandered into the hermitage. Enchanted by Rama's divine beauty, she approached him "
        "with amorous intentions, transforming herself into a beautiful woman. Rama gently "
        "declined, pointing to his married state and directing her to Lakshmana in jest. "
        "When Lakshmana also refused, Surpanakha's desire turned to rage. She attacked Sita "
        "in her true demonic form, seeking to devour her rival. Lakshmana, acting in Sita's "
        "defense, drew his sword and cut off Surpanakha's nose and ears. Bloodied and humiliated, "
        "she fled shrieking to her brother Khara, who attacked with fourteen thousand rakshasas. "
        "Rama single-handedly destroyed the entire army in a fierce battle. Surpanakha then "
        "flew to Lanka, appearing before Ravana with her mutilated face, describing Sita's "
        "incomparable beauty. She planted the seed of desire in Ravana's mind — the seed "
        "that would eventually destroy his entire kingdom."
    ),
    "characters": ["Rama", "Sita", "Lakshmana", "Surpanakha", "Khara"],
    "key_events": [
        "Surpanakha approaches Rama with amorous intent and is rejected",
        "Lakshmana cuts Surpanakha's nose when she attacks Sita",
        "Rama destroys Khara's army of fourteen thousand rakshasas alone"
    ],
    "philosophical_themes": ["karma", "dharma", "courage"],
    "lesser_known_facts": [
        "Valmiki states Rama killed 14,000 rakshasas in approximately 90 minutes — a detail that emphasizes his divine warrior nature far beyond mortal capacity",
        "Surpanakha's husband was actually killed by Ravana himself in a political dispute — her hatred had complex family roots beyond this encounter"
    ],
    "debate_angles": [
        "Was Lakshmana's mutilation of Surpanakha proportionate to her aggression, or was it excessive punishment that triggered a chain of destruction?"
    ],
    "modern_relevance": [
        "Actions have cascading consequences — one moment of disproportionate response can trigger conflicts far beyond the original scope, a lesson in measured reactions"
    ],
    "suggested_angles": ["debate", "what_if"]
})

SEGMENTS.append({
    "kanda_index": 3,
    "kanda_name": "Aranya Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "The Golden Deer (Maricha)",
    "content": (
        "Ravana commanded the demon Maricha to take the form of an enchanting golden deer "
        "and lure Rama away from the hermitage. Maricha, who still bore the trauma of Rama's "
        "arrow at Vishwamitra's yajna, protested — he warned Ravana that pursuing Sita would "
        "destroy Lanka. But Ravana threatened death, leaving Maricha no choice. The golden "
        "deer appeared near Panchavati, its hide shimmering like liquid sunlight with silver "
        "spots. Sita, captivated by its beauty, asked Rama to capture it. Lakshmana warned "
        "that no natural deer could shine thus — it must be a rakshasa trap. But Sita's "
        "innocent desire and Rama's wish to please her prevailed. Rama took his bow and "
        "pursued the deer deep into the forest. When his arrow finally struck, Maricha "
        "reverted to his true form and with his dying breath mimicked Rama's voice crying "
        "'Ha Sita! Ha Lakshmana!' — the deception that would separate the divine couple "
        "and set the great war in motion."
    ),
    "characters": ["Rama", "Sita", "Lakshmana", "Maricha", "Ravana"],
    "key_events": [
        "Ravana forces Maricha to become a golden deer as bait",
        "Sita desires the golden deer despite Lakshmana's warning",
        "Rama pursues and kills Maricha who mimics Rama's voice in distress"
    ],
    "philosophical_themes": ["divine leela", "karma", "dharma"],
    "lesser_known_facts": [
        "Maricha actually warned Ravana extensively about Rama's power — Valmiki dedicates several chapters to Maricha's counsel, making him one of the most tragic characters",
        "Lakshmana explicitly told Sita the deer was unnatural — his warning was specific and logical, not vague, making the subsequent blame on him deeply unfair"
    ],
    "debate_angles": [
        "Was Maricha a villain or a victim — forced to choose between death by Ravana or death by Rama, did he have any real agency in his actions?"
    ],
    "modern_relevance": [
        "Desire for the superficially beautiful over the genuinely valuable leads to vulnerability — recognizing traps disguised as opportunities is crucial in modern decision-making"
    ],
    "suggested_angles": ["character_study", "what_if"]
})

SEGMENTS.append({
    "kanda_index": 3,
    "kanda_name": "Aranya Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "The Abduction of Sita",
    "content": (
        "Hearing Maricha's imitation of Rama's cry, Sita was consumed with fear. She urged "
        "Lakshmana to go help Rama immediately. Lakshmana assured her that no being in three "
        "worlds could harm Rama, but Sita, in panic, accused him of wanting Rama dead to "
        "claim her — words that cut Lakshmana like a sword. Bound by those cruel words, "
        "Lakshmana left to find Rama, drawing a protective line around the cottage — the "
        "Lakshmana Rekha. With the hermitage unguarded, Ravana appeared disguised as an "
        "ascetic seeking alms. Sita, bound by dharma of hospitality, stepped beyond the "
        "protective boundary. Ravana seized her in his true form. The mighty Jatayu, the "
        "aged eagle-king and friend of Dasharatha, attacked Ravana's chariot fearlessly. "
        "A terrible battle ensued in the sky. Though aged and outmatched, Jatayu fought "
        "with the fury of dharma until Ravana severed his wings. Sita was carried away "
        "over the ocean toward Lanka, dropping her ornaments as markers along the path."
    ),
    "characters": ["Sita", "Lakshmana", "Ravana", "Jatayu", "Maricha"],
    "key_events": [
        "Sita forces Lakshmana to leave with harsh words",
        "Ravana disguised as an ascetic abducts Sita when she crosses Lakshmana Rekha",
        "Jatayu battles Ravana in the sky to save Sita but is fatally wounded"
    ],
    "philosophical_themes": ["dharma", "courage", "sacrifice", "karma"],
    "lesser_known_facts": [
        "The Lakshmana Rekha concept is not found in Valmiki's original text — it was added in later versions like Tulsidas's Ramcharitmanas, though a protective boundary is implied",
        "Jatayu was described by Valmiki as being as old as Dasharatha — his battle with Ravana lasted long enough for Ravana's chariot to be damaged significantly"
    ],
    "debate_angles": [
        "Was Ravana's disguise as a Brahmin the greatest adharma — using sacred identity for evil — or was violating hospitality dharma by abducting a guest-giver worse?"
    ],
    "modern_relevance": [
        "Standing up against injustice regardless of personal cost — Jatayu's hopeless fight against a vastly superior foe teaches that courage is not about winning, but about refusing to be a silent witness"
    ],
    "suggested_angles": ["unknown_facts", "why"]
})

SEGMENTS.append({
    "kanda_index": 3,
    "kanda_name": "Aranya Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "Rama's Search and Jatayu's Death",
    "content": (
        "Returning to the empty hermitage, Rama's heart shattered. He wandered the forest "
        "calling Sita's name, asking trees, rivers, and animals if they had seen her. His "
        "grief was overwhelming — the divine avatar experiencing fully human pain. Then he "
        "found Jatayu, lying broken on the earth with severed wings, clinging to life only "
        "to deliver his message. With his last breaths, Jatayu told Rama that Ravana had "
        "taken Sita southward. Rama held the dying eagle-king in his arms like a father, "
        "tears streaming freely. He performed full funeral rites for Jatayu — the same "
        "sacred ceremonies due to a father — declaring that Jatayu's sacrifice was equal to "
        "dying in battle for dharma. This act revealed Rama's boundless compassion: in his "
        "darkest hour of personal loss, he paused to honor a friend's sacrifice. Jatayu "
        "attained moksha through Rama's grace. Armed with the knowledge of Sita's direction, "
        "Rama and Lakshmana began their purposeful journey southward, their grief transformed "
        "into determination."
    ),
    "characters": ["Rama", "Lakshmana", "Jatayu"],
    "key_events": [
        "Rama returns to find the hermitage empty and searches desperately",
        "Dying Jatayu reveals Ravana took Sita southward",
        "Rama performs full father's funeral rites for Jatayu and grants him moksha"
    ],
    "philosophical_themes": ["devotion", "sacrifice", "love", "dharma"],
    "lesser_known_facts": [
        "Valmiki specifically states Rama performed 'pitr-kriya' (father's funeral rites) for Jatayu — the same level of ritual respect as for one's own father, unprecedented for a bird",
        "Rama's grief at the empty hermitage is described in deeply human terms by Valmiki — he asks flowers, deer, and rivers about Sita, showing his avatar experiencing genuine mortal emotion"
    ],
    "debate_angles": [
        "Could Jatayu have chosen to fly for help instead of fighting Ravana alone — was his direct confrontation brave or strategically unwise?"
    ],
    "modern_relevance": [
        "Gratitude and honoring sacrifice matters — Rama's pause to perform rites for Jatayu amid his own crisis teaches that acknowledging others' sacrifices must never be delayed or forgotten"
    ],
    "suggested_angles": ["life_lesson", "hidden_meaning"]
})

# ============================================================
# KANDA 4 - KISHKINDHA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 4,
    "kanda_name": "Kishkindha Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "Meeting Hanuman",
    "content": (
        "Journeying southward, Rama and Lakshmana arrived at the shores of Lake Pampa near "
        "Rishyamukha mountain, where the exiled Vanara king Sugriva lived in hiding from his "
        "brother Vali. Sugriva, spotting the armed princes, feared they were sent by Vali "
        "to kill him. He dispatched his minister Hanuman — disguised as a Brahmin ascetic — "
        "to assess their intentions. The moment Hanuman beheld Rama, something ancient "
        "stirred within him. His scholarly disguise fell away as devotion overwhelmed him. "
        "He revealed his true form and fell at Rama's feet. Rama, struck by Hanuman's "
        "eloquent Sanskrit and noble bearing, told Lakshmana that one who speaks thus must "
        "have mastered all Vedas and grammar. This first meeting between Rama and Hanuman "
        "was the beginning of the most celebrated bond of devotion in all scripture. Hanuman "
        "carried both brothers on his shoulders to Sugriva's hideout on the mountain, "
        "initiating the alliance that would change the course of destiny."
    ),
    "characters": ["Rama", "Lakshmana", "Hanuman", "Sugriva"],
    "key_events": [
        "Rama and Lakshmana arrive at Rishyamukha mountain",
        "Hanuman meets Rama disguised as a Brahmin and instantly recognizes his divinity",
        "Hanuman carries both brothers to Sugriva's hideout"
    ],
    "philosophical_themes": ["devotion", "divine leela", "dharma"],
    "lesser_known_facts": [
        "Rama praised Hanuman's speech specifically — Valmiki records Rama saying anyone who speaks thus must know all four Vedas, six Vedangas, and mastered Vyakarana grammar",
        "Hanuman initially approached in Brahmin disguise because Sugriva feared the princes were Vali's assassins — his intelligence gathering role is often overlooked"
    ],
    "debate_angles": [
        "Was Sugriva justified in his paranoia about Vali sending assassins, or did his fear reveal a weakness that made him unfit to rule even before Vali's injustice?"
    ],
    "modern_relevance": [
        "First impressions of character matter — Rama recognized Hanuman's greatness through his speech and bearing, teaching that how we communicate reveals our inner cultivation"
    ],
    "suggested_angles": ["character_study", "unknown_facts"]
})

SEGMENTS.append({
    "kanda_index": 4,
    "kanda_name": "Kishkindha Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Alliance with Sugriva",
    "content": (
        "On Rishyamukha mountain, Sugriva shared his tragic story with Rama. His brother "
        "Vali, king of Kishkindha, had stolen his wife Ruma and driven him into exile under "
        "threat of death. Sugriva lived in constant fear, confined to Rishyamukha — the one "
        "place Vali was cursed never to enter. Rama, moved by Sugriva's plight and recognizing "
        "a parallel to his own exile, proposed an alliance: he would defeat Vali and restore "
        "Sugriva's kingdom, and in return Sugriva would deploy his vast monkey armies to find "
        "Sita. They sealed this pact with fire as witness. Sugriva showed Rama the ornaments "
        "Sita had dropped from the sky during her abduction — confirmation that she was taken "
        "southward. Rama could identify only her anklets, saying he never looked above Sita's "
        "feet due to respect. Lakshmana, who served Sita daily, confirmed the ornaments. "
        "This bond between a human prince and a vanara king, forged in mutual suffering, "
        "would prove to be the strategic alliance that ultimately defeated Ravana's empire."
    ),
    "characters": ["Rama", "Lakshmana", "Sugriva", "Hanuman"],
    "key_events": [
        "Sugriva tells Rama his story of exile by brother Vali",
        "Rama and Sugriva form an alliance sealed by fire",
        "Sita's fallen ornaments shown as proof of her abduction route"
    ],
    "philosophical_themes": ["dharma", "duty", "devotion"],
    "lesser_known_facts": [
        "Rama said he could only identify Sita's anklets because he never raised his gaze above her feet out of respect — this reveals the profound reverence in their relationship",
        "Vali was cursed by a sage never to enter Rishyamukha — without this curse, Sugriva would have had nowhere safe to hide, making it a crucial plot detail"
    ],
    "debate_angles": [
        "Was Sugriva's alliance with Rama purely strategic self-interest, or did genuine friendship develop between two exiled leaders sharing similar fates?"
    ],
    "modern_relevance": [
        "Strategic alliances built on mutual need and shared values create unstoppable partnerships — Rama's alliance with Sugriva shows how collaboration amplifies individual strengths"
    ],
    "suggested_angles": ["hidden_meaning", "character_study"]
})

SEGMENTS.append({
    "kanda_index": 4,
    "kanda_name": "Kishkindha Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "The Defeat of Vali",
    "content": (
        "Sugriva challenged Vali to single combat as planned, but Vali's might was overwhelming. "
        "In the first duel, Rama could not distinguish between the two brothers and held his "
        "arrow. Sugriva retreated, wounded and angry. Rama explained his dilemma and asked "
        "Sugriva to wear a garland as identification. In the second challenge, as Vali emerged "
        "furious despite his wife Tara's prophetic warning, Rama's arrow struck him from "
        "behind a tree. The dying Vali confronted Rama with a powerful question — how could "
        "a righteous prince strike from hiding? Rama's response was measured: Vali had stolen "
        "his brother's wife, an act of adharma deserving punishment; as a king upholding "
        "dharma, Rama had authority to punish. Furthermore, hunting animals from concealment "
        "was accepted practice, and Vali was a vanara. Vali, recognizing divine justice, "
        "accepted his fate and entrusted his son Angada to Rama's protection. His death "
        "remains one of the most debated moments in the epic, questioning the boundaries "
        "of dharmic warfare."
    ),
    "characters": ["Rama", "Sugriva", "Vali", "Tara", "Angada", "Lakshmana"],
    "key_events": [
        "First duel fails when Rama cannot distinguish Vali from Sugriva",
        "Rama strikes Vali with an arrow from behind a tree in the second duel",
        "Dying Vali questions Rama's righteousness and entrusts his son Angada"
    ],
    "philosophical_themes": ["dharma", "karma", "duty"],
    "lesser_known_facts": [
        "Vali's wife Tara specifically warned him not to fight again — she had heard of Rama's alliance and predicted Vali's death, making his pride his undoing",
        "Rama gave multiple justifications for killing Vali — including that kings have the right to punish adharma anywhere in their realm, even in animal kingdoms"
    ],
    "debate_angles": [
        "Was Rama's killing of Vali from concealment a violation of Kshatriya dharma, or was it justified given Vali's boon that took half his opponent's strength in face-to-face combat?"
    ],
    "modern_relevance": [
        "Power without justice creates tyranny — Vali's strength meant no one could challenge him directly, teaching that systems must ensure even the powerful are accountable"
    ],
    "suggested_angles": ["debate", "why"]
})

SEGMENTS.append({
    "kanda_index": 4,
    "kanda_name": "Kishkindha Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "The Search for Sita",
    "content": (
        "With Sugriva crowned king of Kishkindha, the massive search for Sita began. Sugriva "
        "dispatched millions of vanaras in all four directions, giving each group one month. "
        "The southern party, led by Angada with Hanuman, Jambavan, and Nala, was considered "
        "most crucial since Jatayu had indicated Sita was taken south. After weeks of "
        "fruitless searching through mountains and forests, the southern party discovered "
        "a hidden cave that transported them magically, costing precious days. Emerging near "
        "the southern ocean, they despaired — the month had expired and Sugriva's punishment "
        "for failure was death. As they contemplated mass suicide rather than return empty-handed, "
        "the aged vulture Sampati — Jatayu's brother — appeared. Learning of his brother's "
        "heroic death, Sampati revealed he had seen Ravana carry a weeping woman across the "
        "ocean to Lanka, one hundred yojanas away. Now they needed someone capable of crossing "
        "the vast ocean. All eyes turned to Hanuman, the son of Vayu."
    ),
    "characters": ["Hanuman", "Angada", "Jambavan", "Sugriva", "Sampati"],
    "key_events": [
        "Massive vanara armies dispatched in all four directions to find Sita",
        "Southern party reaches the ocean shore and despairs",
        "Sampati reveals Lanka is one hundred yojanas across the ocean"
    ],
    "philosophical_themes": ["devotion", "courage", "duty"],
    "lesser_known_facts": [
        "The southern search party entered a magical cave called Swayamprabha's cave — they were trapped for days, which is why their month expired, a detail that adds urgency",
        "Sampati had lost his wings years ago while shielding Jatayu from the sun — his sacrifice for his brother mirrors the devotion theme throughout the Ramayan"
    ],
    "debate_angles": [
        "Was Sugriva's death threat for failure in the search a sign of kingly authority or a cruel overreach that nearly drove loyal warriors to suicide?"
    ],
    "modern_relevance": [
        "Breakthroughs often come at the point of despair — the search party found crucial intelligence from Sampati precisely when they had given up, teaching that persistence through hopelessness yields answers"
    ],
    "suggested_angles": ["unknown_facts", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 4,
    "kanda_name": "Kishkindha Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "Hanuman Prepares to Leap",
    "content": (
        "With Lanka identified across the vast ocean, Jambavan turned to Hanuman and began "
        "reminding him of his forgotten powers. As a child, Hanuman had leaped toward the sun "
        "mistaking it for a fruit. Indra struck him, and the gods cursed him to forget his "
        "divine abilities until reminded by another. Jambavan's words broke the curse — "
        "Hanuman's eyes widened as cosmic memory flooded back. He was the son of Vayu, the "
        "wind god, with power equal to his father. As confidence filled him, Hanuman began "
        "to expand. His form grew massive — towering over trees, then mountains, until he "
        "stood like a second mountain himself. The vanaras watched in awe as Hanuman ascended "
        "Mount Mahendra, the peak groaning under his weight. He faced south toward the "
        "invisible Lanka, one hundred yojanas away. With a mighty roar that shook the earth, "
        "he crouched, compressed his enormous power, and prepared for the greatest leap in "
        "all creation. The mountain sank into the earth from the force. Hanuman launched "
        "himself skyward, splitting clouds, his shadow racing across the ocean below."
    ),
    "characters": ["Hanuman", "Jambavan", "Angada"],
    "key_events": [
        "Jambavan reminds Hanuman of his forgotten divine powers",
        "Hanuman expands to his massive cosmic form",
        "Hanuman leaps from Mount Mahendra across the ocean toward Lanka"
    ],
    "philosophical_themes": ["devotion", "courage", "divine leela"],
    "lesser_known_facts": [
        "Hanuman forgot his powers due to a curse from sages whose meditation he disrupted as a playful child — the curse was specifically that he would not remember until someone reminded him",
        "Valmiki describes Mount Mahendra sinking into the earth from the force of Hanuman's leap — trees flew upward, animals scattered, and the ocean parted below his trajectory"
    ],
    "debate_angles": [
        "Was the curse on Hanuman's memory a necessary divine mechanism to ensure he served Rama rather than acting independently, or was it an unjust punishment of an innocent child?"
    ],
    "modern_relevance": [
        "We often forget our own potential until someone believes in us — Jambavan's role in awakening Hanuman mirrors how mentors and coaches unlock capabilities we cannot see in ourselves"
    ],
    "suggested_angles": ["hidden_meaning", "life_lesson"]
})

# ============================================================
# KANDA 5 - SUNDARA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 5,
    "kanda_name": "Sundara Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "Hanuman's Leap Across the Ocean",
    "content": (
        "Hanuman soared across the hundred-yojana ocean like a divine missile, his body "
        "casting a massive shadow on the waters below. The ocean, respecting Rama's mission, "
        "raised Mount Mainaka from its depths offering rest, but Hanuman touched it briefly "
        "and continued — duty before comfort. Then came trials: Surasa, mother of serpents, "
        "opened her mouth wide demanding he enter before passing. Hanuman cleverly expanded "
        "until she expanded too, then instantly shrank to thumb-size, entered and exited her "
        "mouth in a flash. She blessed him, revealing it was a divine test. The shadow-demon "
        "Simhika grabbed his shadow from below, pulling him down. Hanuman recognized the "
        "threat, expanded again, and tore through her with devastating force. Finally, as "
        "dusk fell, the golden spires of Lanka appeared on the distant shore — a magnificent "
        "city gleaming like a second sun upon the Trikuta mountain. Hanuman shrank to the "
        "size of a cat and landed silently on Lanka's ramparts under cover of darkness, "
        "beginning his sacred mission to find Sita."
    ),
    "characters": ["Hanuman", "Surasa", "Simhika"],
    "key_events": [
        "Hanuman leaps 100 yojanas, touching Mount Mainaka briefly",
        "Overcomes Surasa's test through cleverness rather than force",
        "Kills shadow-demon Simhika and reaches Lanka at nightfall"
    ],
    "philosophical_themes": ["devotion", "courage", "divine leela"],
    "lesser_known_facts": [
        "Mount Mainaka rose from the ocean as gratitude — it was once sheltered by Vayu (Hanuman's father) when Indra was cutting off all mountains' wings, so it repaid the debt",
        "Surasa was actually sent by the devas as a test — she blessed Hanuman after he outsmarted her, confirming his worthiness for the mission"
    ],
    "debate_angles": [
        "Were the obstacles on Hanuman's path (Surasa, Simhika, Mainaka) divine tests or genuine threats — does it diminish his heroism if they were pre-arranged?"
    ],
    "modern_relevance": [
        "Intelligence over brute force — Hanuman's approach to Surasa shows that creative problem-solving within constraints outperforms direct confrontation"
    ],
    "suggested_angles": ["hidden_meaning", "unknown_facts"]
})

SEGMENTS.append({
    "kanda_index": 5,
    "kanda_name": "Sundara Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Searching Lanka",
    "content": (
        "Under the cover of moonlit night, Hanuman explored Lanka in his diminished form, "
        "marveling at its extraordinary splendor. The city was beyond imagination — golden "
        "ramparts, crystal palaces, gardens with wish-fulfilling trees, streets paved with "
        "gems. He infiltrated Ravana's inner palace, passing through chambers of unimaginable "
        "luxury. In Ravana's private quarters, he found countless beautiful women sleeping — "
        "queens and captives alike. For a moment, Hanuman worried he had committed sin by "
        "gazing upon sleeping women, but reasoned that his purpose was righteous and his mind "
        "unstained. He searched the drinking halls where Ravana lay in drunken sleep, massive "
        "and terrible even unconscious, his ten heads crowned in gold. Hanuman searched every "
        "chamber, garden, and tower but could not find Sita. His heart sank — had she perished? "
        "Had she been consumed? Then he remembered: a woman of Sita's virtue would never be "
        "found in Ravana's pleasure quarters. He must search elsewhere — the gardens, the "
        "groves where an imprisoned devotee might pray."
    ),
    "characters": ["Hanuman", "Ravana"],
    "key_events": [
        "Hanuman infiltrates Lanka at night in miniature form",
        "Explores Ravana's palace marveling at its impossible wealth",
        "Searches all chambers but does not find Sita among Ravana's women"
    ],
    "philosophical_themes": ["devotion", "dharma", "courage"],
    "lesser_known_facts": [
        "Valmiki has Hanuman engage in ethical self-debate about looking at sleeping women — he concludes his mind had no impure intent, showing his deeply dharmic consciousness",
        "Lanka's description in Valmiki spans multiple chapters — it was not just rich but architecturally advanced with aerial pathways, mechanical gardens, and multi-level structures"
    ],
    "debate_angles": [
        "Was Ravana's Lanka a testament to his genius as a ruler and architect, or was its wealth built entirely on plunder and conquest — can greatness coexist with evil?"
    ],
    "modern_relevance": [
        "Ethical reasoning during difficult missions — Hanuman's self-debate about propriety while searching teaches that maintaining moral standards under pressure defines true character"
    ],
    "suggested_angles": ["unknown_facts", "character_study"]
})

SEGMENTS.append({
    "kanda_index": 5,
    "kanda_name": "Sundara Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "Finding Sita in Ashoka Vatika",
    "content": (
        "Hanuman found Sita in the Ashoka Vatika — a garden grove beneath an ancient Ashoka "
        "tree. She was emaciated, dressed in a single soiled garment, surrounded by fierce "
        "rakshasi guards. Her beauty, though diminished by months of captivity and grief, "
        "still shone like a flame through smoke. Ravana arrived with dawn, adorned in royal "
        "splendor, pleading and threatening alternately. He offered her the position of chief "
        "queen, dominion over all his wives, limitless wealth. Sita placed a blade of grass "
        "between them — a gesture of absolute contempt — and replied that Ravana was as far "
        "beneath Rama as a jackal is beneath a lion. Enraged, Ravana gave her two months to "
        "submit or be killed. After he left, the rakshasis threatened her with torture and "
        "consumption. Sita despaired, contemplating ending her life, when a small figure "
        "in the tree above began softly singing the story of Rama — Hanuman had found her "
        "at last."
    ),
    "characters": ["Sita", "Hanuman", "Ravana"],
    "key_events": [
        "Hanuman discovers Sita beneath an Ashoka tree, captive and grief-stricken",
        "Ravana threatens Sita with a two-month ultimatum",
        "Sita places a grass blade between them in absolute rejection of Ravana"
    ],
    "philosophical_themes": ["devotion", "courage", "dharma", "love"],
    "lesser_known_facts": [
        "The grass blade (trina) Sita placed between herself and Ravana was a Vedic gesture meaning 'you are as insignificant as this straw to me' — a deeply learned insult",
        "Valmiki describes Sita contemplating suicide by hanging from the Ashoka tree — Hanuman's arrival was literally moments before she may have acted"
    ],
    "debate_angles": [
        "Was Ravana's restraint in not forcing himself on Sita due to a curse (touching an unwilling woman would kill him) or genuine warped respect — does motivation matter if the outcome protects?"
    ],
    "modern_relevance": [
        "Unshakeable conviction in one's values — Sita's absolute refusal despite months of psychological torture teaches that identity and principles cannot be broken by external pressure alone"
    ],
    "suggested_angles": ["character_study", "hidden_meaning"]
})

SEGMENTS.append({
    "kanda_index": 5,
    "kanda_name": "Sundara Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "Hanuman Reveals Himself to Sita",
    "content": (
        "Waiting until the guards slept, Hanuman descended from the tree in his small form, "
        "approaching Sita with folded hands. He identified himself as Rama's messenger and "
        "presented Rama's signet ring as proof. Sita's eyes filled with tears of relief — "
        "the first hope in months of darkness. Hanuman narrated Rama's grief, his alliance "
        "with Sugriva, and the vast army preparing for her rescue. He offered to carry Sita "
        "back to Rama on his shoulders immediately. But Sita refused with wisdom — she would "
        "not touch another male, and Rama must come himself to defeat Ravana, vindicating "
        "his honor. She gave Hanuman her Chudamani — a hair ornament that only Rama would "
        "recognize — along with a personal memory only they shared: the story of a crow "
        "that once attacked her and how Rama punished it with the Brahmastra. This intimate "
        "detail would prove her identity beyond doubt. Hanuman bowed, his mission of "
        "discovery complete. Now he would announce his presence to Lanka."
    ),
    "characters": ["Hanuman", "Sita", "Rama"],
    "key_events": [
        "Hanuman presents Rama's signet ring to Sita as proof of identity",
        "Sita refuses to be carried back, insisting Rama must come and fight",
        "Sita gives Hanuman her Chudamani and a personal message for Rama"
    ],
    "philosophical_themes": ["devotion", "love", "dharma", "duty"],
    "lesser_known_facts": [
        "The crow incident Sita referenced was about Jayanta (Indra's son) who attacked her — Rama used a Brahmastra on a crow, showing he would use supreme weapons even for a minor threat to Sita",
        "Sita refused Hanuman's offer to escape not from helplessness but from dharmic principle — she wanted Rama to defeat Ravana properly, not sneak her away"
    ],
    "debate_angles": [
        "Was Sita's refusal to escape with Hanuman a missed strategic opportunity, or was her insistence on Rama fighting Ravana essential for establishing cosmic justice?"
    ],
    "modern_relevance": [
        "Hope delivered at the darkest hour transforms everything — Hanuman's message shows the power of being a messenger of hope for those who feel abandoned"
    ],
    "suggested_angles": ["unknown_facts", "why"]
})

SEGMENTS.append({
    "kanda_index": 5,
    "kanda_name": "Sundara Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "Burning of Lanka",
    "content": (
        "Rather than return quietly, Hanuman chose to assess Lanka's military strength. He "
        "deliberately destroyed the Ashoka Vatika, drawing out warriors. He defeated thousands "
        "of rakshasas and even Ravana's son Akshaya Kumar. Finally, Indrajit (Meghanada) "
        "captured him with a Brahmastra — Hanuman could have resisted but chose capture "
        "to meet Ravana face-to-face. In Ravana's court, Hanuman delivered Rama's message "
        "with thundering authority: return Sita or face annihilation. Ravana, enraged, ordered "
        "Hanuman's death. Vibhishana intervened — killing a messenger violates all dharma. "
        "Instead, Ravana ordered Hanuman's tail set ablaze as humiliation. But as the rakshasas "
        "wrapped his ever-growing tail in oil-soaked cloth, Sita prayed to Agni to be cool "
        "to Hanuman. The fire did not burn him. Hanuman broke free and leaped across Lanka's "
        "rooftops, his flaming tail igniting the golden city. Palace after palace, tower after "
        "tower burned. Lanka blazed like a funeral pyre. Then Hanuman extinguished his tail "
        "in the ocean and flew back triumphantly to deliver news to Rama."
    ),
    "characters": ["Hanuman", "Ravana", "Indrajit", "Vibhishana", "Sita", "Akshaya Kumar"],
    "key_events": [
        "Hanuman destroys Ashoka Vatika and defeats waves of rakshasa warriors",
        "Captured by Indrajit, Hanuman confronts Ravana directly in court",
        "Tail set on fire, Hanuman burns Lanka and returns triumphant to Rama"
    ],
    "philosophical_themes": ["courage", "devotion", "divine leela", "dharma"],
    "lesser_known_facts": [
        "Hanuman allowed himself to be captured by Indrajit's Brahmastra — he could resist it but chose capture strategically to deliver Rama's ultimatum directly to Ravana",
        "Valmiki states Sita prayed to Agni that fire be cool to Hanuman — this is why the flames did not burn his body despite engulfing everything else"
    ],
    "debate_angles": [
        "Was Vibhishana's defense of Hanuman in Ravana's court an act of dharma or an early sign of his loyalty shifting toward Rama's side?"
    ],
    "modern_relevance": [
        "Turning a punishment into an advantage — Hanuman converted his humiliation into Lanka's destruction, teaching that resilient people transform setbacks into strategic opportunities"
    ],
    "suggested_angles": ["life_lesson", "hidden_meaning"]
})

# ============================================================
# KANDA 6 - YUDDHA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 6,
    "kanda_name": "Yuddha Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "Building the Bridge (Ram Setu)",
    "content": (
        "With Hanuman's intelligence confirmed, Rama marched south with Sugriva's vast "
        "vanara army — millions strong, shaking the earth with their march. At the southern "
        "shore, the ocean stretched impossibly wide. Rama prayed to the ocean god Sagara for "
        "three days, but received no response. In rare anger, Rama raised the Brahmastra "
        "to dry the ocean. Terrified, Sagara appeared and suggested a bridge. Nala, son of "
        "Vishwakarma the divine architect, possessed the boon that anything he threw in water "
        "would float. Under his direction, millions of vanaras carried boulders and trees "
        "to the shore. Each stone inscribed with Rama's name floated on the waves. A small "
        "squirrel contributed by rolling in sand and shaking it off onto the bridge — Rama "
        "stroked its back in gratitude, creating its distinctive stripes. In five days, "
        "the hundred-yojana bridge was complete — a miracle of devotion and engineering "
        "spanning the mighty ocean. The army crossed, and Lanka's doom drew near."
    ),
    "characters": ["Rama", "Lakshmana", "Hanuman", "Sugriva", "Nala", "Sagara"],
    "key_events": [
        "Rama threatens to dry the ocean when Sagara ignores his prayers",
        "Nala directs the bridge construction with floating stones bearing Rama's name",
        "The bridge (Ram Setu) completed in five days, army crosses to Lanka"
    ],
    "philosophical_themes": ["devotion", "courage", "divine leela"],
    "lesser_known_facts": [
        "Nala specifically had a boon from Vishwakarma (his father) that anything he threw would float — it was not just the name of Rama but Nala's boon that enabled the bridge",
        "Valmiki describes Rama's anger at the ocean as so intense that sea creatures began dying — Lakshmana had to calm him, showing even avatars experienced wrath"
    ],
    "debate_angles": [
        "Was the ocean god Sagara's initial silence a deliberate test of Rama's patience, or simple arrogance of an elemental deity toward a mortal king?"
    ],
    "modern_relevance": [
        "Every contribution matters regardless of size — the squirrel's story teaches that in great endeavors, even the smallest effort made with devotion equals the mightiest contribution"
    ],
    "suggested_angles": ["unknown_facts", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 6,
    "kanda_name": "Yuddha Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Vibhishana Joins Rama",
    "content": (
        "Before the war, a pivotal defection changed its course. Vibhishana, Ravana's younger "
        "brother, had repeatedly counseled Ravana to return Sita and avoid destruction. In "
        "Lanka's final war council, Vibhishana stood alone against Ravana's ministers urging "
        "war, pleading that dharma demanded Sita's release. Ravana kicked him from the throne "
        "room, calling him a traitor. Vibhishana flew across the ocean with four loyal "
        "companions and sought refuge with Rama. Sugriva and others advised suspicion — a "
        "defector from the enemy could be a spy. But Rama declared his principle: anyone "
        "who comes seeking shelter with folded hands must be accepted, even if they carry "
        "risk. He crowned Vibhishana as the future king of Lanka on the spot. Vibhishana "
        "provided crucial intelligence — Ravana's military formations, weapon locations, "
        "the secret of his immortality, and Lanka's defensive weaknesses. This single act "
        "of dharmic defection proved more strategically valuable than ten thousand warriors."
    ),
    "characters": ["Vibhishana", "Rama", "Ravana", "Sugriva", "Lakshmana", "Hanuman"],
    "key_events": [
        "Vibhishana counsels Ravana to return Sita and is expelled from Lanka",
        "Rama accepts Vibhishana despite allies' suspicion and crowns him future king",
        "Vibhishana provides critical intelligence about Lanka's defenses"
    ],
    "philosophical_themes": ["dharma", "courage", "truth", "duty"],
    "lesser_known_facts": [
        "Rama crowned Vibhishana king of Lanka BEFORE the war even began — this was a strategic and dharmic statement that the war was about justice, not conquest",
        "Vibhishana revealed that Ravana had a boon — he could not be killed unless the nectar of immortality stored in his navel was dried by celestial weapons"
    ],
    "debate_angles": [
        "Was Vibhishana a traitor to his brother and kingdom, or was his defection the highest form of patriotism — saving Lanka from destruction caused by one man's ego?"
    ],
    "modern_relevance": [
        "Whistleblowers face the same dilemma as Vibhishana — choosing organizational loyalty versus higher ethical duty, teaching that speaking truth to power requires sacrificing belonging"
    ],
    "suggested_angles": ["debate", "character_study"]
})

SEGMENTS.append({
    "kanda_index": 6,
    "kanda_name": "Yuddha Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "The Battle Begins",
    "content": (
        "The war erupted with devastating fury. Rama's vanara army clashed with Lanka's "
        "rakshasa forces in battles that shook heaven and earth. The first days saw "
        "extraordinary heroism — Angada fought Ravana's generals, Nila battled Ravana himself "
        "briefly, and Hanuman wreaked havoc through enemy lines. But Ravana's son Indrajit "
        "(Meghanada) proved the deadliest threat. Using his mastery of illusion warfare, "
        "Indrajit became invisible and rained Nagastra — serpent arrows — upon the army. "
        "Rama and Lakshmana themselves fell unconscious, bound by supernatural serpents. "
        "The entire army despaired. Garuda, king of birds and eternal enemy of serpents, "
        "descended and freed them. Later, in a devastating night attack, Indrajit's "
        "Shakti weapon struck Lakshmana in the chest. He lay dying, his life force fading. "
        "The physician Sushena declared only the Sanjeevani herb from the Himalayas could "
        "save him before sunrise. Hanuman flew north, unable to identify the herb, lifted "
        "the entire Dronagiri mountain, and returned before dawn. Lakshmana was revived."
    ),
    "characters": ["Rama", "Lakshmana", "Hanuman", "Indrajit", "Angada", "Garuda"],
    "key_events": [
        "Indrajit uses Nagastra to incapacitate Rama and Lakshmana",
        "Lakshmana struck by Shakti weapon, lies dying",
        "Hanuman carries entire Dronagiri mountain to save Lakshmana with Sanjeevani"
    ],
    "philosophical_themes": ["courage", "devotion", "sacrifice", "dharma"],
    "lesser_known_facts": [
        "Indrajit made himself invisible during battle using Brahma's boon — Valmiki describes the entire vanara army being unable to fight what they could not see, a form of ancient stealth warfare",
        "Hanuman flew to the Himalayas and back in one night — Valmiki describes him passing over Ayodhya where Bharata nearly shot him down, not recognizing him"
    ],
    "debate_angles": [
        "Was Indrajit's use of invisibility and illusion in warfare legitimate strategy or cowardly violation of Kshatriya combat rules?"
    ],
    "modern_relevance": [
        "When someone you love is in crisis, no obstacle is too great — Hanuman moving a mountain teaches that devotion-fueled determination makes the impossible achievable"
    ],
    "suggested_angles": ["unknown_facts", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 6,
    "kanda_name": "Yuddha Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "Fall of Kumbhakarna and Indrajit",
    "content": (
        "Ravana, desperate, awakened his brother Kumbhakarna from his divine slumber. "
        "Kumbhakarna, cursed to sleep six months at a time, was a giant of incomprehensible "
        "size. Drums, elephants walking on his body, and oceans of food were needed to rouse "
        "him. Once awake, Kumbhakarna rebuked Ravana for his folly but fought out of brotherly "
        "duty. He waded through the vanara army like a mountain through waves, consuming "
        "warriors by hundreds. Even Sugriva was captured in his fist. But Rama systematically "
        "severed his limbs with divine arrows — first arms, then legs — before the final "
        "arrow took his head. The ground shook when Kumbhakarna fell. Indrajit remained the "
        "final barrier. Through Vibhishana's intelligence, Lakshmana discovered Indrajit "
        "performing a yajna to become truly invincible. Attacking before its completion, "
        "Lakshmana fought a grueling duel. With the Indrastra — weapon of Indra himself — "
        "Lakshmana severed Indrajit's head. Ravana's last great warrior was dead. The path "
        "to Ravana stood open."
    ),
    "characters": ["Rama", "Lakshmana", "Kumbhakarna", "Indrajit", "Ravana", "Vibhishana", "Sugriva"],
    "key_events": [
        "Kumbhakarna awakened and devastates the vanara army before Rama slays him",
        "Lakshmana interrupts Indrajit's invincibility yajna on Vibhishana's advice",
        "Lakshmana defeats and kills Indrajit with the Indrastra"
    ],
    "philosophical_themes": ["duty", "karma", "courage", "dharma"],
    "lesser_known_facts": [
        "Kumbhakarna actually told Ravana he was wrong but chose to fight anyway out of family loyalty — Valmiki portrays him as morally aware but duty-bound, not mindlessly evil",
        "Indrajit was performing a ritual that would make him completely invincible — Vibhishana's specific knowledge of its timing and location was the decisive intelligence"
    ],
    "debate_angles": [
        "Was Kumbhakarna more honorable than Ravana — fighting despite disagreeing with the cause — or equally culpable for enabling his brother's adharma through support?"
    ],
    "modern_relevance": [
        "Strategic intelligence wins wars — Vibhishana's insider knowledge about Indrajit's ritual timing teaches that information advantage often matters more than raw power"
    ],
    "suggested_angles": ["character_study", "debate"]
})

SEGMENTS.append({
    "kanda_index": 6,
    "kanda_name": "Yuddha Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "Ravana's Fall and Victory",
    "content": (
        "The final battle between Rama and Ravana was cosmic in scale. Ravana charged in his "
        "great chariot with ten heads gleaming, wielding weapons from every divine armory he "
        "had conquered. Rama, standing on the ground, faced him on Indra's chariot sent from "
        "heaven. Their arrows collided in mid-air like meteors. Rama severed Ravana's heads, "
        "but they regenerated instantly. The battle raged for days. Finally, Sage Agastya "
        "appeared and taught Rama the Aditya Hridayam — a hymn to the Sun god for invincible "
        "power. Empowered by this divine prayer, Rama fitted the Brahmastra to his bow — "
        "an arrow crafted by Brahma himself, with wind in its feathers, sun and fire in its "
        "tip, and the weight of Mount Meru. The arrow struck Ravana's navel, destroying the "
        "nectar of immortality stored there. The great king of Lanka fell, and the three "
        "worlds trembled. Flowers rained from heaven. Rama declared no enmity with the dead "
        "and ordered honorable last rites for Ravana. Lanka was liberated, and dharma "
        "restored to the world."
    ),
    "characters": ["Rama", "Ravana", "Sage Agastya", "Lakshmana", "Vibhishana"],
    "key_events": [
        "Rama and Ravana fight a cosmic multi-day battle",
        "Sage Agastya teaches Rama the Aditya Hridayam hymn",
        "Rama destroys Ravana with Brahmastra targeting his navel, dharma restored"
    ],
    "philosophical_themes": ["dharma", "karma", "courage", "divine leela"],
    "lesser_known_facts": [
        "The Aditya Hridayam taught mid-battle by Sage Agastya is a real hymn preserved in tradition — it is considered one of the most powerful prayers and is recited to this day",
        "Rama ordered full royal funeral rites for Ravana and asked Vibhishana to perform them — he declared that enmity ends with death, showing extraordinary magnanimity"
    ],
    "debate_angles": [
        "Was Ravana a great king destroyed by one fatal flaw (lust), or was his entire reign built on the adharma of conquering through force — was Lanka's prosperity just?"
    ],
    "modern_relevance": [
        "One fatal character flaw can destroy a lifetime of achievement — Ravana's brilliance in every other domain makes his fall a powerful cautionary tale about unchecked desire"
    ],
    "suggested_angles": ["life_lesson", "why"]
})

# ============================================================
# KANDA 7 - UTTARA KANDA
# ============================================================
SEGMENTS.append({
    "kanda_index": 7,
    "kanda_name": "Uttara Kanda",
    "chapter": 1,
    "segment_index": 1,
    "title": "Return to Ayodhya (Pushpaka Vimana)",
    "content": (
        "With Ravana defeated and Sita rescued, the time of exile had ended. Rama, Sita, "
        "Lakshmana, and their allies boarded the Pushpaka Vimana — Ravana's captured flying "
        "chariot that moved by thought alone. As they soared northward, Rama pointed out "
        "landmarks to Sita: the bridge, Kishkindha, Panchavati, and the rivers they had "
        "crossed in sorrow now gleaming below in the light of victory. Hanuman flew ahead "
        "to inform Bharata, who had counted every day of fourteen years. Bharata, true to "
        "his vow, had prepared the ceremonial fire — if Rama did not return on the exact "
        "day, he would enter it. Hanuman reached Nandigrama moments before the deadline. "
        "When the Pushpaka descended over Ayodhya, the city exploded in celebration. "
        "Citizens lit thousands of oil lamps to guide Rama home — the first Deepavali. "
        "Bharata ran barefoot to embrace Rama, his fourteen years of ascetic waiting finally "
        "rewarded. The sandals were removed from the throne. Ayodhya's king had returned."
    ),
    "characters": ["Rama", "Sita", "Lakshmana", "Bharata", "Hanuman"],
    "key_events": [
        "Return journey on Pushpaka Vimana, the thought-controlled flying chariot",
        "Hanuman reaches Bharata just before his self-immolation deadline",
        "Ayodhya lights thousands of lamps welcoming Rama — origin of Deepavali"
    ],
    "philosophical_themes": ["devotion", "love", "dharma", "divine leela"],
    "lesser_known_facts": [
        "Bharata had genuinely prepared to enter fire if Rama was even one day late — Hanuman's advance message arrived with barely hours to spare according to Valmiki",
        "The Pushpaka Vimana is described as a self-propelled aerial vehicle that could expand to hold any number of passengers and moved according to the rider's mental commands"
    ],
    "debate_angles": [
        "Was Bharata's vow to immolate himself if Rama was late an act of supreme devotion or was it emotionally manipulative pressure that could have devastated the kingdom?"
    ],
    "modern_relevance": [
        "Keeping promises against all odds — Rama returning on the exact promised day and Bharata's unwavering wait teach that trust is built when commitments are honored precisely"
    ],
    "suggested_angles": ["unknown_facts", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 7,
    "kanda_name": "Uttara Kanda",
    "chapter": 2,
    "segment_index": 2,
    "title": "Rama's Coronation (Ram Rajya)",
    "content": (
        "The coronation of Rama was the most magnificent ceremony the three worlds had "
        "witnessed. Sacred waters from every holy river were brought by divine messengers. "
        "Sage Vasishtha performed the rituals as Rama ascended the golden throne with Sita "
        "beside him. Kings from across Bharatavarsha attended, devas watched from the heavens, "
        "and the earth itself seemed to bloom in celebration. Thus began Ram Rajya — the "
        "golden age of perfect governance. Under Rama's rule, no one died prematurely, no "
        "disease touched the people, rains came on time, harvests were abundant, and every "
        "citizen was content. Rama ruled not through fear but through dharma — he was "
        "accessible to the poorest citizen, decided disputes with perfect justice, and "
        "placed his duty to the people above personal happiness. He gifted riches to all "
        "allies — Vibhishana ruled Lanka justly, Sugriva prospered in Kishkindha, and "
        "Hanuman remained ever at Rama's feet. The concept of Ram Rajya became the eternal "
        "standard against which all governance is measured."
    ),
    "characters": ["Rama", "Sita", "Bharata", "Lakshmana", "Hanuman", "Sage Vasishtha"],
    "key_events": [
        "Grand coronation ceremony with waters from all sacred rivers",
        "Beginning of Ram Rajya — the golden age of perfect dharmic rule",
        "Rama rewards all allies and establishes justice for every citizen"
    ],
    "philosophical_themes": ["dharma", "duty", "love", "sacrifice"],
    "lesser_known_facts": [
        "Valmiki describes Ram Rajya in specific terms — no premature death, no widows weeping, no thieves, no fear — it was a literal utopia maintained through Rama's personal dharma",
        "Rama gave the Pushpaka Vimana back to its original owner Kubera — despite winning it in war, he did not keep what rightfully belonged to another"
    ],
    "debate_angles": [
        "Is Ram Rajya an achievable governance model or an idealized standard that sets impossible expectations for real human rulers?"
    ],
    "modern_relevance": [
        "Leadership is service — Ram Rajya teaches that a leader's success is measured not by personal glory but by the wellbeing of the most vulnerable citizens"
    ],
    "suggested_angles": ["hidden_meaning", "life_lesson"]
})

SEGMENTS.append({
    "kanda_index": 7,
    "kanda_name": "Uttara Kanda",
    "chapter": 3,
    "segment_index": 3,
    "title": "The Trial of Sita (Agni Pariksha)",
    "content": (
        "Despite the glorious homecoming, whispers plagued the kingdom. Citizens questioned "
        "Sita's purity after months in Ravana's captivity. When Rama heard a washerman "
        "publicly doubting Sita, the weight of kingship pressed upon him. As a husband, Rama "
        "never doubted Sita — but as a king, he felt bound to maintain public faith in the "
        "royal house. The Agni Pariksha was arranged — Sita would walk into sacred fire to "
        "prove her purity. Before the assembled court and divine witnesses, Sita stepped "
        "into the blazing flames with serene composure. Agni himself rose from the fire, "
        "holding Sita unharmed, and testified before all that she was purer than the fire "
        "itself. The devas appeared, confirming her absolute chastity. Sita emerged radiant, "
        "vindicated by the very elements. Yet this moment carries profound sadness — that "
        "such proof was demanded of one whose devotion never wavered through unspeakable "
        "suffering. It remains the most emotionally complex passage in the entire epic."
    ),
    "characters": ["Rama", "Sita", "Agni"],
    "key_events": [
        "Public doubt about Sita's purity reaches Rama's ears",
        "Sita enters fire with serene composure for the Agni Pariksha",
        "Agni and devas testify to Sita's absolute purity, she emerges unharmed"
    ],
    "philosophical_themes": ["dharma", "sacrifice", "truth", "duty"],
    "lesser_known_facts": [
        "In Valmiki's version, the Agni Pariksha happened immediately after the war in Lanka before returning — the later exile of Sita is a separate event from a different section",
        "Agni declared that Sita's thoughts never strayed to anyone but Rama even in her darkest moments — the fire god certified not just physical but mental purity"
    ],
    "debate_angles": [
        "Was the washerman who triggered the crisis speaking legitimate democratic concern, or was public gossip given undue power over royal family privacy?"
    ],
    "modern_relevance": [
        "The tension between personal relationships and public accountability — leaders today face the same dilemma of sacrificing private happiness for public perception"
    ],
    "suggested_angles": ["debate", "why"]
})

SEGMENTS.append({
    "kanda_index": 7,
    "kanda_name": "Uttara Kanda",
    "chapter": 4,
    "segment_index": 4,
    "title": "Lava and Kusha",
    "content": (
        "When public doubt persisted despite the Agni Pariksha, Rama made his most painful "
        "decision — sending the pregnant Sita to the forest to preserve dharmic governance. "
        "Lakshmana, weeping, left Sita at Sage Valmiki's ashram. There, Sita gave birth to "
        "twin sons — Lava and Kusha. They grew up in the ashram under Valmiki's guidance, "
        "learning the Vedas, warfare, and music. Valmiki himself composed the Ramayan and "
        "taught the twins to sing it. Years later, when Rama performed the Ashwamedha Yajna, "
        "two young boys appeared and sang the complete Ramayan before the royal court with "
        "voices so pure they moved every listener to tears. Rama recognized the story of "
        "his own life and noticed the boys' resemblance. When Valmiki revealed their identity, "
        "Rama's heart broke and rejoiced simultaneously. His sons stood before him — raised "
        "without a father, yet carrying his every virtue. The Ramayan thus comes full circle — "
        "composed by the sage who sheltered Sita, sung by the sons who never knew their father."
    ),
    "characters": ["Rama", "Sita", "Lava", "Kusha", "Sage Valmiki", "Lakshmana"],
    "key_events": [
        "Sita sent to Valmiki's ashram where she gives birth to Lava and Kusha",
        "Valmiki composes the Ramayan and teaches it to the twins",
        "Lava and Kusha sing the Ramayan before Rama at the Ashwamedha Yajna"
    ],
    "philosophical_themes": ["sacrifice", "dharma", "love", "karma"],
    "lesser_known_facts": [
        "Valmiki composed the Ramayan DURING the events — he was a contemporary of Rama, not a later poet, and the twins singing it before Rama is the epic being performed to its own protagonist",
        "Lava and Kusha learned martial arts so well that they actually defeated Rama's army guarding the Ashwamedha horse — not knowing it was their father's"
    ],
    "debate_angles": [
        "Was Rama's abandonment of pregnant Sita for public opinion the greatest failure of duty as a husband, or the ultimate sacrifice of personal happiness for dharmic kingship?"
    ],
    "modern_relevance": [
        "Art preserves truth when systems fail — Valmiki's Ramayan sung by the twins represents how storytelling and culture carry justice forward when institutions cannot"
    ],
    "suggested_angles": ["why", "hidden_meaning"]
})

SEGMENTS.append({
    "kanda_index": 7,
    "kanda_name": "Uttara Kanda",
    "chapter": 5,
    "segment_index": 5,
    "title": "Sita's Return to Earth and Rama's Legacy",
    "content": (
        "Rama asked Sita to return to the palace and prove her purity once more before the "
        "people. Sita, who had endured years of exile for a doubt she never deserved, rose "
        "with quiet dignity. She spoke not in anger but in calm resolve: if she had never "
        "thought of anyone but Rama, let Mother Earth receive her. The ground trembled. "
        "A golden throne rose from the split earth, borne by divine serpents. Bhumi Devi — "
        "Mother Earth herself — appeared and took Sita into her embrace. Sita descended "
        "into the earth from which she was born, returning to her origin. Rama lunged "
        "forward in grief but could not stop her. His anguish was boundless. The avatar "
        "who defeated Ravana could not prevent this loss. Rama ruled alone for thousands "
        "of years afterward, Sita's golden image beside his throne. When his purpose was "
        "complete, Rama walked into the Sarayu river, returning to his divine Vishnu form. "
        "His eternal legacy — the triumph of dharma through sacrifice — endures beyond time."
    ),
    "characters": ["Rama", "Sita", "Bhumi Devi", "Lava", "Kusha"],
    "key_events": [
        "Sita calls upon Mother Earth to receive her as proof of her purity",
        "Earth opens and Bhumi Devi takes Sita back, she returns to her origin",
        "Rama's eventual departure into Sarayu river, returning to Vishnu form"
    ],
    "philosophical_themes": ["dharma", "sacrifice", "love", "divine leela", "renunciation"],
    "lesser_known_facts": [
        "Rama ruled for 11,000 years after Sita's departure according to Valmiki — he never remarried, placing Sita's golden image beside him during all rituals requiring a wife",
        "Rama's final departure is called 'Jal Samadhi' — he walked into the Sarayu river with citizens who chose to leave with him, and all attained divine liberation"
    ],
    "debate_angles": [
        "Was the repeated demand for Sita to prove herself a failure of Ayodhya's citizens rather than Rama — should public opinion ever override divine testimony already given?"
    ],
    "modern_relevance": [
        "The cost of leadership — Rama's personal grief beneath the crown teaches that the highest positions often demand the deepest personal sacrifices that no one else sees"
    ],
    "suggested_angles": ["life_lesson", "hidden_meaning"]
})

# ============================================================
# FILE GENERATION LOGIC
# ============================================================
KANDA_DIRS = {
    1: "1_bala_kanda",
    2: "2_ayodhya_kanda",
    3: "3_aranya_kanda",
    4: "4_kishkindha_kanda",
    5: "5_sundara_kanda",
    6: "6_yuddha_kanda",
    7: "7_uttara_kanda",
}


def main():
    created_count = 0
    for segment in SEGMENTS:
        kanda_idx = segment["kanda_index"]
        seg_idx = segment["segment_index"]
        kanda_dir = KANDA_DIRS[kanda_idx]
        segments_dir = os.path.join(BASE_DIR, kanda_dir, "segments")
        os.makedirs(segments_dir, exist_ok=True)

        filename = f"{seg_idx:03d}.json"
        filepath = os.path.join(segments_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(segment, f, indent=2, ensure_ascii=False)

        created_count += 1
        print(f"  [OK] {kanda_dir}/segments/{filename}")

    print(f"\nTotal segments created: {created_count}")
    print("All 35 segment files generated successfully!")


if __name__ == "__main__":
    main()
