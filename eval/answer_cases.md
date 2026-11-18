# Answer-quality evaluation: cases (for review)

36 cases. Manual questions reuse the retrieval sets' reference answers and evidence quotes;
data questions are checked against live SQL; out-of-scope questions must be declined.

| id | kind | split / category | question | expected |
|---|---|---|---|---|
| m_q01 | manual | dev / lexical | How should porcelain insulators be checked for cracks? | Only when de-energized, tap gently with a small metal object about the size of a 6-inch wrench; a ringing sound means no cracks, a dull and hollow sound means cracked. |
| m_q02 | manual | dev / paraphrase | What noise tells a lineworker that a ceramic unit is damaged when knocked on? | A dull, hollow sound indicates a cracked insulator; a sound one rings. |
| m_q06 | manual | dev / paraphrase | Are a few bullet holes in the sheds of a polymer insulator a serious problem? | A few holes through only the weathersheds have little or no adverse effect; replace the insulator if embedded metal is found in the shank. |
| m_q09 | manual | dev / paraphrase | Why do insulators near the sea need more attention? | Salt deposits build up and materially reduce the flashover value; tenacious deposits may require removal and hand cleaning. |
| m_q12 | manual | dev / paraphrase | Why would a utility pick polymer units for lines in remote rural regions? | Composite insulators are used in outlying areas where shooting vandalism is a problem. |
| m_q19 | manual | dev / lexical | How often should instrument transformers be scheduled for a maintenance inspection? | Every 2 years, plus visual inspection whenever associated apparatus is inspected but not less than every 6 months. |
| m_q20 | manual | dev / paraphrase | How frequently should a substation be checked by eye and with a thermal camera? | Monthly visual and yearly infrared inspections. |
| m_q26 | manual | dev / paraphrase | Is it safe to spray water on lightning protection devices while the line is live? | Energized washing of surge arresters may impose severe electrical stresses from voltage imbalance and should not be done without the arrester manufacturer's consent. |
| m_q33 | manual | dev / lexical | What should be done with insulators that have extensive glaze burns? | Replace them without delay. |
| m_q35 | manual | dev / paraphrase | Why might a failed disc look perfectly fine from the outside? | Punctures usually occur under the head of the insulator, so there may be no visual evidence. |
| m_q38 | manual | dev / lexical | Why do pedestal-type (pin and cap) insulators fail? | Cement growth causes the cap to separate from the porcelain, most often when mounted horizontally. |
| m_q41 | manual | dev / lexical | How often should hot sticks be electrically tested? | Inspect before each use and test every 2 years. |
| m_h01 | manual | heldout / lexical | What problems did the Trinity Plants have with their mercury switches? | Units tripped off or locked out because of false operation of the mercury switches during the first two years of operation. |
| m_h02 | manual | heldout / paraphrase | What can happen when a faulty capacitor used for line communication is left in service? | Defective coupling capacitors can explode, which is why they are Doble tested. |
| m_h05 | manual | heldout / lexical | Which ANSI guide covers grounding of instrument transformer secondary circuits? | ANSI C57.13.3, Guide for the Grounding of Instrument Transformer Secondary Circuits and Cases. |
| m_h08 | manual | heldout / paraphrase | Why do the large oil-filled step-up transformers at hydro plants need extinguishing systems? | They contain thousands of gallons of flammable oil, so Reclamation requires fire suppression for mineral-oil-filled GSU transformers. |
| m_h10 | manual | heldout / paraphrase | What does the device that controls how much water reaches the turbine do? | The governor controls generator power and frequency by regulating water flow to the turbine. |
| m_h13 | manual | heldout / lexical | At what hydrogen concentration can battery gas explode? | Above 8 percent hydrogen (flammable above 4 percent). |
| m_h14 | manual | heldout / paraphrase | How long should I wait after switching off a power factor correction bank before working on it? | At least 5 minutes, then short the terminals to ground and to each other. |
| m_h15 | manual | heldout / lexical | What is the minimum acceptable dielectric breakdown value for transformer oil? | 22 kV for oil (26 kV for RTemp and silicone), per ASTM D 877. |
| m_h16 | manual | heldout / paraphrase | How can a lineworker check protective hand wear for holes before use? | Air test: grasp the cuff, twirl the glove to trap air and check for leaks. |
| m_h19 | manual | heldout / paraphrase | Is it OK to pull the protective links out of a capacitor bank by hand? | No, not unless the capacitors are first discharged and grounded. |
| m_h20 | manual | heldout / paraphrase | In a lighting circuit where the lights are wired one after another, what is the same for every light? | The current (series circuit); the voltage varies. |
| m_h21 | manual | heldout / paraphrase | What should a worker assume about electrical gear until it is proven safe? | That it is energized, until it is known positively (e.g. grounding clamps) that it is not. |
| d01 | data | live SQL | How many inspections are in the system? | 15 inspections (tool: list_inspections or inspection_statistics or fleet_statistics) |
| d02 | data | live SQL | How many detections are currently flagged for human review in total? | 11 detections flagged for human review (tool: fleet_statistics or list_inspections) |
| d03 | data | live SQL | Which inspection or inspections have the most detected insulators, and how many? | inspection(s) 3, 11 with 7 insulators each (tool: list_inspections) |
| d04 | data | live SQL | What is the average inference time of detection runs that escalated from the fast to the accurate model? | about 933 ms on average (tool: fleet_statistics) |
| d05 | data | live SQL | How many inspections were handled by the fast model alone, without escalation? | 8 inspections handled by the fast model alone (tool: list_inspections or fleet_statistics) |
| d06 | data | live SQL | What is the highest YOLO confidence among the detections in inspection 3? | highest confidence 0.73 (tool: get_inspection) |
| d07 | data | live SQL | In inspection 15, how many detections did the vision review judge not to be insulators? | 3 detections judged not to be insulators (tool: get_inspection) |
| d08 | data | live SQL | How many inspections are there per insulator type? | composite: 3, glass: 9, porcelain: 3 (tool: list_inspections) |
| o01 | out_of_scope | - | What minimum clearance does DIN EN 50341 require between a 110 kV conductor and the ground? | Not covered by the knowledge base; the answer must say so and must not invent a value. |
| o02 | out_of_scope | - | What tightening torque should be used for the end fittings of a composite long-rod insulator from a specific manufacturer such as Lapp? | Not covered by the knowledge base; the answer must say so and must not invent a value. |
| o03 | out_of_scope | - | How often does the German transmission operator Amprion wash its insulators? | Not covered by the knowledge base; the answer must say so and must not invent a value. |
| o04 | out_of_scope | - | What is the annual failure rate of glass cap-and-pin insulators in European transmission grids? | Not covered by the knowledge base; the answer must say so and must not invent a value. |
