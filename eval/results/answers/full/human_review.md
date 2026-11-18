# Human review of the judge (blind)

For each case, read the question, the reference, the passages the agent retrieved and
its answer, then fill in the `your ...` lines. The judge's verdicts are not shown here.

- correctness: `correct` (key facts of the reference), `partially_correct`, `incorrect`
- faithful: `yes` if every claim the answer presents as guidance is supported by the
  passages, `no` if any is not (general caveats about its own limits do not count)
- declined (out-of-scope cases): `yes` if it says the sources don't cover it and gives no
  invented value, otherwise `no`

## m_q41

**Question:** How often should hot sticks be electrically tested?

**Reference:** Inspect before each use and test every 2 years.

**Passages the answer cites:**

> [S1] FIST 4-1B Maintenance Scheduling for Electrical Equipment (US Bureau of Reclamation, 2005), p. 80-81: Door and other interlocks Functional test for proper sequence. Switch disconnect studs and finger clusters (if drawout type) Lubricate unless manufacturer’s instruction says not. Cable terminations and connections Clean and inspect for surface tracking; check connections for correct tightness. Meters Check calibration. Fuse clips and fuses Check clips for adequate spring pressure and proper fuse rating. Grounding Check base and operating handle ground connections; see that ground cable is not broken. Potential, current, and control transformers Evaluate and make necessary repairs. Switch operating hot sticks See that switch operating hot sticks are in good condition and are kept in a dry place; inspect hot sticks for damage and deterioration; discard suspect switch operating hot sticks; test hot sticks per requirements under FIST Volume 4-1B, section 25, “Personal Protective Equipment.” References FIST Volume 3-18, Replacing Glaze Burned Insulators
>
> [S2] FIST 4-1B Maintenance Scheduling for Electrical Equipment (US Bureau of Reclamation, 2005), p. 47-48: 26 24. Motors (< 500 hp) Motors of this type drive pumps, valves, gates, and fans. They are usually induction motors and are generally less than 500 hp but may be somewhat larger. Critical motors should routinely be tested. Insulation resistance (Megger®) Annually FIST Volume 3-4, 2.2 Infrared scan Annually NFPA 70B, 20-17.5 Personal protective equipment is used by maintenance workers to provide protection from hazardous electrical energy. Integrity of this equipment is paramount, so maintenance should be scheduled and accomplished similar to equipment maintenance. Hot Line Tools Review equipment ratings 5 years NERC Planning Standard FAC-009-1 Safety ground - visual inspection Annually and before each use NFPA 70E, 130.7 FIST Volume 5-1 Safety ground - millivolt drop test Annually FIST Volume 5-1 Hot stick cleaning, inspection, and electrical test Inspect before each use; test every 2 years OSHA 1910.269J(iii) IEEE Std. 978 Gloves, sleeves, blankets tests Annually Manufacturer’s instruction manuals NFPA 70E, 130.7 IEEE 978
>

**Answer:**

**Every 2 years for the electrical test, plus an inspection before each use.**

- FIST 4-1B's maintenance schedule says hot sticks need cleaning, inspection and an electrical test: "Inspect before each use; test every 2 years." It cites OSHA 1910.269 and IEEE Std. 978 as the basis [S2].
- The same schedule says to review the ratings of hot line tools every 5 years [S2].
- For switch-operating hot sticks in particular: keep them in good condition and store them somewhere dry. Check them for damage and wear, throw away any you're unsure about, and test them under FIST 4-1B section 25, "Personal Protective Equipment" [S1].

**Caveat:** This comes from a 2005 US Bureau of Reclamation manual. The OSHA and IEEE references may have been updated since then. If you work under EU or German rules, check the current requirements for live-working tools, such as the relevant DIN EN / IEC standards and your employer's safety rules, before relying on the 2-year interval.

- your correctness: 
- your faithful: 

## m_q35

**Question:** Why might a failed disc look perfectly fine from the outside?

**Reference:** Punctures usually occur under the head of the insulator, so there may be no visual evidence.

**Passages the answer cites:**

> [S1] FIST Volumes 3-18 to 3-28, Miscellaneous Electrical Volumes II (US Bureau of Reclamation, 2000); includes 3-18 Replacing Glaze Burned Insulators and 3-26 Failures of Pedestal-Type Insulators, p. 4: Replacing Glaze Burned Insulators It is recommended that damaged or suspected damaged transmission line and station insulators be immediately replaced to reduce the probability of in service failures and subsequent outages. Very few insulators are punctured in service, since a surface flashover usually occurs before puncture. When puncture does occur, it is usually the result of small cracks in porcelain started by cement growth or mechanical or thermal shock. Since a puncture usually occurs under the head of the insulator, there may be no visual evidence of the damage. The only reliable method of detecting the puncture is electrical test. The Doble test method has proven quite reliable. Large arc burns on transmission and bus insulators indicate that the insulators have been subjected to electrical and thermal stress, which could cause complete failure at a later time. A number of trans­ mission line suspension insulators, which had been damaged by flash burns, were tested by the Doble method, and it was found that they did not meet acceptable standards for good insulators.
>
> [S2] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 22: Defective insulators can also cause visible corona or interference voltage propagation. b. Related material . Apparatus type insulators are provided in substations to support devices and heavy lines. See chapter 4, section XII, which provides a discussion of insulation levels. Radio interference conditions may be detected by using instruments designed for this purpose. Otherwise, maintenance tests on insulators are normally limited to occasional power factor measurements at the more important installations, where the loss of the facilities must be kept to an absolute minimum. Bus and switch insulators should be power-factor tested in conjunction with similar testing of other apparatus within the substation. Power factor tests are described in section VII. Switch-and-bus apparatus type insulators are the most intricate type and require the highest degree of reliability in service. This is because the several pieces of porcelain and hardware, assembled in a single unit, are usually located at key positions in the systems, where failure is extremely serious.
>

**Answer:**

**Because the puncture is usually hidden under the cap.** When a porcelain disc is punctured, the break usually happens under the head of the insulator, so there may be no visible sign of damage from outside [S1].

**How it happens:**
- Punctures in service are rare, because the surface usually flashes over before the porcelain breaks through [S1].
- When a puncture does happen, it usually starts as small cracks in the porcelain. These come from cement growth (the cement holding the cap expands over time) or from mechanical or thermal shock [S1].
- Discs with large arc burns have been through electrical and thermal stress that can cause complete failure later, even if they look acceptable now. Flash-burned suspension insulators that were tested did not meet acceptable standards for good insulators [S1].

**How to find them:**
- The manual says the only reliable way to detect a puncture is an electrical test, and the Doble method has proven reliable [S1].
- TM 5-684 says faulty insulators can also show up as visible corona or radio interference, which instruments can detect. At important sites, maintenance testing is mostly power-factor measurement [S2].

**What this means for drone inspection:** The YOLOv8 detections and the AI condition reviews only work from visible features, so they can't rule out a punctured disc. A "no visible defect" result doesn't confirm a disc is electrically sound. Arc-burned or suspect units should be electrically tested or replaced; the manual recommends replacing damaged or suspect insulators right away [S1].

These sources are older US federal manuals (1996–2000). For current test practice, check the applicable standards, such as IEC / DIN EN.

- your correctness: 
- your faithful: 

## m_h19

**Question:** Is it OK to pull the protective links out of a capacitor bank by hand?

**Reference:** No, not unless the capacitors are first discharged and grounded.

**Passages the answer cites:**

> [S1] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 103: .- c. Replacing fuses on capacitor installations. Fuses used on capacitors should not be removed or replaced by hand, unless due precautions are taken beforehand to discharge and ground the capacitors in accordance with chapter 13, section II. The entire capacitor bank should be disconnected and grounded while replacing the fuses, unless the fuse link or its mounting, or both, can be removed safely and completely from the circuit using hot line tools. d. Replacing of vented fuses . Vented fuses being replaced within this venting area should be deenergized during replacement. Vented fuses, operable from outside their vented area, may be replaced without deenergizing the circuit, but the use of hearing protectors is recommended. e. Replacing of current-limiting nonvented type. Careless handling of these inherently fragile fuses may result in damage. When damage is suspected, the fuse should not be used. f. Expendable cap cutouts . Do not install a nonexpendable cap on an expendable cap cutout because of the resulting reduction of the expendable cap cutout’s interrupting capability.
>
> [S2] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 144: Fixed shunt capacitors are used to improve the voltage level and switched shunt capacitors are used to improve voltage regulation. Capacitor installations will generally be connected grounded wye because of undesirable effects of other connections. All capacitor banks should be equipped with a means to disconnect them from the electric system. Some systems utilize ungrounded connections to minimize interference and because this connection is considered easy to fuse. Capacitors containing polychlorinated biphenyl (PCB) should have been disposed of under the procedures of the Environmental Protection Agency to implement the Toxic Substances Control Act of marked as containin g PCB’s. ANSI/IEEE 18 now requires an impregnant identification visible from the ground with a glue color used to designate a nonPCB liquid. Capacitors retain a charge after they ar e deenergized. After capacitors are deenergized allow at least 5 minutes for discharge and then short the capacitor terminals to ground and to each other. These grounding provisions should remain until work on the installation is completed.
>
> [S3] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 181: Verify that panelboard loads are balanced, where applicable, and check wiring and grounds. A majority of power quality problems result from loose connections and improper grounding techniques,and unbalanced loads. If correcting these deficiencies does not alleviate excessive harmonics, then harmonic mitigation measures must be developed utilizing engineering solutions beyond the scope of this manual. AIthough harmonic mitigation is not the responsibility of the electrical supervisor, it is the supervisor’s responsibility to kee p informed on both the quantity and quality of electrical service available to facility users. Therefore, an awareness of apparatus actions, which may indicate unacceptable harmonic levels, is necessary to determine where more precise data should be acquired. a. Capacitors .Capacitor impedance decreases with frequency, and a capacitor bank acts as a harmonic sink where most harmonic problems are first noticed. Fuse blowing, without any obvious reason, or a capacitor unit failure, can be signs of a possible harmonic problem. A supply system inductance, in resonance with the capacitor bank, can cause large currents and voltages to develop.
>
> [S5] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 144: After capacitors are deenergized allow at least 5 minutes for discharge and then short the capacitor terminals to ground and to each other. These grounding provisions should remain until work on the installation is completed. Although most power capacitors have a discharge resistor installed to automatically discharge them after they are disconnected from the circuit, it is not advisable to depend entirely on such resistors for safety. The initial inspection should be made within 24 hours after energizing a new capacitor installation. This inspection should be made at a time of maximum circuit voltage, usually during the first period of light load on the circuit. In addition to visual observations, this inspection should include voltage and current readings to ensure that voltages and currents do not exceed capacitor rating limits. Operating kilovars (the sum of the fundamental frequency kilovars and any harmonic frequency kilovars) should not exceed 135 percent of the capacitor rating. Routine maintenance and inspection should be accomplished at least four times per year.
>

**Answer:**

**No, not unless the bank has been disconnected, discharged and grounded first.** TM 5-684 says capacitor fuses should not be removed or replaced by hand unless the capacitors have already been discharged and grounded [S1].

**What the manual requires:**
- **Disconnect and ground the whole bank** while you replace fuses. The only exception is when you can take the fuse link or its mounting safely and completely out of the circuit using hot-line tools [S1].
- **Wait, then short the terminals.** Capacitors stay charged after they are de-energized. Wait at least 5 minutes, then short the terminals to ground and to each other [S2], [S5].
- **Don't trust the built-in discharge resistors.** Most capacitors have one, but the manual says not to rely on it alone for safety [S5].
- **Keep the grounds on** until all work on the installation is finished [S5].

**Related points:**
- **Vented fuses:** If you're working inside the venting area, de-energize them before replacing them. If they can be operated from outside that area, hearing protection is recommended [S1].
- **Fuses blowing for no clear reason:** This can point to a harmonic or resonance problem. Find the cause rather than just replacing the fuses [S3].

This guidance comes from a 1996 US Army manual. In Germany or the EU, follow your current national rules, such as DIN VDE 0105-100 / EN 50110 (the "five safety rules"), and your company's switching and grounding procedures.

- your correctness: 
- your faithful: 

## m_h01

**Question:** What problems did the Trinity Plants have with their mercury switches?

**Reference:** Units tripped off or locked out because of false operation of the mercury switches during the first two years of operation.

**Passages the answer cites:**

> [S1] FIST Volumes 3-18 to 3-28, Miscellaneous Electrical Volumes II (US Bureau of Reclamation, 2000); includes 3-18 Replacing Glaze Burned Insulators and 3-26 Failures of Pedestal-Type Insulators, p. 6: Correction for Faulty Operation of Mercury Switches For approximately the first two years of operation of the Trinity Plants, problems were experienced with the units tripping off or locking out due to false operation of the mercury switches. This trouble was first experienced by the Lewiston Construction Office personnel before these plants were transferred to operation and maintenance status. Investigation of this repetitive problem disclosed that operation of these mercury switches (thrust bearing oil level-, turbine bearing oil level, thrust and lower guide bearing oil temperature switches, and occasionally others) was initiated by vibration. This vibration was greatest as the units were synchro­ nized on the line and as the units passed through rough loading ranges. The troubles initiated by rough synchronizing were corrected by proper ad­ justment of the automatic synchronizer. It was found that the mercury switches were mounted practically flat and heavy vibration caused the mercury to splash, momentarily closing the con­ tacts.
>
> [S3] FIST Volumes 3-18 to 3-28, Miscellaneous Electrical Volumes II (US Bureau of Reclamation, 2000); includes 3-18 Replacing Glaze Burned Insulators and 3-26 Failures of Pedestal-Type Insulators, p. 6: The troubles initiated by rough synchronizing were corrected by proper ad­ justment of the automatic synchronizer. It was found that the mercury switches were mounted practically flat and heavy vibration caused the mercury to splash, momentarily closing the con­ tacts. Anti-vibration type mercury switches were purchased by the Lewiston Office for the thrust bearing oil high and low level interlocks on each generator as these were the switches that had caused the greatest number of false operations. The antivibration mercury switches have been very satisfactory after minor adjustment on the slope of the mercury tube. False operation of the remaining mercury switches has been corrected by relocating some of the switches to locations where they are subject to less vibration and by adjusting the mounting to increase the slope of the mercury tube to prevent the mercury from splashing. Therefore, it has not been necessary to replace any of the remaining mercury switches with the anti-vibration type. 1 (FIST 3-19 6/91)
>

**Answer:**

At the Trinity Plants, mercury switches falsely operated because of vibration. For about the first two years, this caused the generating units to trip off or lock out [S1].

**What went wrong**
- The false operations affected the thrust bearing and turbine bearing oil-level switches, the thrust and lower guide bearing oil-temperature switches, and sometimes others [S1].
- The switches were mounted almost flat. Heavy vibration made the mercury splash and briefly close the contacts [S1][S3].
- Vibration was worst when the units were synchronized onto the line and when they ran through rough loading ranges [S1].
- Lewiston Construction Office staff first saw the problem before the plants were handed over to operation and maintenance [S1].

**How it was fixed**
- **Rough synchronizing:** solved by properly adjusting the automatic synchronizer [S3].
- **Thrust bearing oil high/low level interlocks:** these caused the most false trips, so they were replaced with anti-vibration mercury switches on each generator. These worked well after a small adjustment to the slope of the mercury tube [S3].
- **The other switches:** some were moved to spots with less vibration, and the mountings were adjusted to tilt the mercury tube more steeply so the mercury couldn't splash. None of these had to be replaced with anti-vibration switches [S3].

Source: USBR FIST Volume 3-19 (6/91). This is an older US Bureau of Reclamation document about a specific plant, not a general standard.

- your correctness: 
- your faithful: 

## m_h10

**Question:** What does the device that controls how much water reaches the turbine do?

**Reference:** The governor controls generator power and frequency by regulating water flow to the turbine.

**Passages the answer cites:**

> [S1] FIST 4-1B Maintenance Scheduling for Electrical Equipment (US Bureau of Reclamation, 2005), p. 46: Stator winding - power factor measurements (Doble) Nonroutine. May be performed in conjunction with other generator condition tests. Stator core - physical inspection During 1-, 2½-, and 5-year warranty inspections; thereafter, during major maintenance outages but not to exceed 5 years. Stator core - core magnetizing test Nonroutine. Should be performed prior to rewind or if core has been damaged. Rotor - physical inspection During major maintenance outages but not to exceed 5 years. Rotor - insulation resistance polarization (Megger®) Nonroutine. Performed when deterioration is suspected. Rotor - AC pole drop test Nonroutine. Performed when deterioration is suspected. Thrust and upper guide bearing insulation test Annually per FIST Volume 5-11. Governors control generator power and frequency output by regulating water flow to the turbine. Governors may be mechanical type or electrohydraulic type having electronic controls. New digital governors substitute digital control circuits for analog electronic controls of older electrohydraulic governors. Mechanical governor maintenance is fully described in FIST Volume 2-3, Mechanical Governors for Hydraulic Units.
>
> [S2] FIST 4-1B Maintenance Scheduling for Electrical Equipment (US Bureau of Reclamation, 2005), p. 46-47: New digital governors substitute digital control circuits for analog electronic controls of older electrohydraulic governors. Mechanical governor maintenance is fully described in FIST Volume 2-3, Mechanical Governors for Hydraulic Units. Mechanical maintenance requirements for all types of governors are identified in FIST Volume 4-1A, Maintenance Scheduling for Mechanical Equipment. The electrical maintenance schedule below supplements these mechanical maintenance requirements. Preventive maintenance Per manufacturer’s recommendations Manufacturer’s instruction manuals Control system alignment 5 years Reclamation Recommended Practice Equipment grounding is an essential part of protecting staff and equipment from high potential caused by electrical faults. Equipment grounding conductors are subject to failure due to corrosion, loose connections, and mechanical damage. Grounding may also be compromised during equipment addition and removal or other construction-type activities. Periodically verifying grounding system integrity is an important maintenance activity. Substations/Switchyards Visual inspection, tighten connectors Annually PEB No. 26 24. Motors (< 500 hp) Motors of this type drive pumps, valves, gates, and fans. They are usually induction motors and are generally less than 500 hp but may be somewhat larger. Critical motors should routinely be tested.
>

**Answer:**

That device is the **governor**. It controls the generator's power and frequency output by regulating how much water flows to the turbine [S1].

**Types:**
- **Mechanical** governors [S1].
- **Electrohydraulic** governors, which use electronic controls [S1].
- **Digital** governors, a newer kind that replace the analog electronics of older electrohydraulic units with digital control circuits [S1][S2].

**Maintenance:**
- Preventive maintenance follows the manufacturer's recommendations [S2].
- The control system alignment is checked every 5 years [S2].
- Mechanical maintenance is covered in FIST Volume 2-3 (mechanical governors) and FIST Volume 4-1A (mechanical equipment scheduling) [S1][S2].

The passages I found don't explain how the governor moves the water-control parts, such as the wicket gates, or how its control loop works. For that, you'd need FIST Volume 2-3 or the manufacturer's manual, and neither is in this knowledge base. These are also older US Bureau of Reclamation documents (2005), not current EU/German standards.

- your correctness: 
- your faithful: 

## m_q19

**Question:** How often should instrument transformers be scheduled for a maintenance inspection?

**Reference:** Every 2 years, plus visual inspection whenever associated apparatus is inspected but not less than every 6 months.

**Passages the answer cites:**

> [S3] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 25-26: A current transformer, being a constant-current device, requires that the secondary circuit always be closed. As long as there is current in the primary winding, there will be current in the secondary winding. On an open circuit the voltage will be the secondary current multiplied by an extremely high open-circuit secondary resistance. This is a voltage which may both damage insulation and prove dangerous to life. Under no circumstances should the secondary of a current transformer be opened while the primary circuit of the transformer is energized, unless the terminals of the current transformer are of th e shortcircuiting type. Instrument transformers should be scheduled for a maintenance inspection every 2 years. In addition, they should be inspected visually any tim e appara3-7 tus with which they are associated is inspected, but not less than every 6 months. a. Safety. Before performing any maintenance on instrument transformers, they must be deenergized and completely isolated from any energized source .Isolation may be accomplished by opening applicable disconnect switches or fuses or by de-energizing appropriate circuit breakers.
>
> [S4] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 18-19: Calibration should provide the full-scale accuracy based on the manufacturer’s data, usuall y 1 percent for switchboard instruments and 0.25 percent fo r portable instruments. Dated calibration labels should be visible and up-to-date calibration records, instructions, and procedures should be maintained for each instrument which should have had a calibrating standard of higher accuracy than that of the test instrument. ._ c. Test reports. A dated test report should include, as a minimum, the following data: (1) Summary of project findings and recommendations, if required for additional work. (2) Description of equipment tested. (3) Description of test. (4) Test results. The intervals given in this manual and/or by manufacturer’s maintenance recommendations should be considered an initial interval for normal conditions. Intervals should be shortened where adverse conditions exist and may be lengthened only where experience under better-than-normal conditions show this can be done safely. The frequency of inspection may vary for similar equipment operating under different conditions. Critical equipment, heavily loaded apparatus, operator handled, and intermittently operated units are examples of different operating conditions. - - TRANSMISSION AND DISTRIBUTION SUBSTATIONS
>
> [S5] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 26: Safety. Before performing any maintenance on instrument transformers, they must be deenergized and completely isolated from any energized source .Isolation may be accomplished by opening applicable disconnect switches or fuses or by de-energizing appropriate circuit breakers. In polyphase circuits, all phases must be disconnected to ensure that instrument transformers are not energized through interconnected secondaries. Drawout-type voltage transformers, used in metalclad switchgear, should be completely withdrawn for maintenance. b. Procedure. Maintain bushings and terminals of instrument transformers as described in section VII. Maintain fuses, if present, as described in chapter 8, section II. (1) Case. Inspect case or tank for evidence of corrosion and leaks. Clean and paint as required. Instrument transformers that show evidence of leaks should be replaced with those of the same rating and returned to a shop for repair. (2) Conduit and connection . Tighten all loose joints in conduit around fittings, terminal boxes and supporting clamps. Clean and paint corroded areas. Verify tightness of all bolted connections. Verify that wiring, grounding, and shorting connections provide good contact. (3) Drawout mechanisms.
>

**Answer:**

Under US Army TM 5-684 (1996), you should **schedule a maintenance inspection of instrument transformers every 2 years** [S3]. You should also:

- **Inspect them visually** whenever you inspect the equipment they're connected to, and **at least every 6 months** [S3].
- **De-energize and fully isolate them before any maintenance.** In polyphase circuits, disconnect all phases so the transformers can't be energized through connected secondaries [S3], [S5].

These intervals are a starting point for normal conditions. Inspect more often where conditions are harsh. Only stretch the intervals if experience under better-than-normal conditions shows that's safe [S4].

The two maintenance visits should cover [S5]:
- **Case:** check for corrosion and leaks. Replace any unit that leaks.
- **Conduit and connections:** tighten loose joints and bolted connections.
- **Wiring, grounding and shorting connections:** confirm they make good contact.
- **Bushings, terminals and fuses:** maintain them as described in the manual.

**Safety note:** never open the secondary of a current transformer while its primary is energized, unless the terminals are the short-circuiting type. An open secondary can produce dangerous voltages [S3].

This is a 1996 US military manual. Check your utility's own procedures, the manufacturer's recommendations and current standards such as DIN EN / IEC, which may set different intervals.

- your correctness: 
- your faithful: 

## o02

**Question:** What tightening torque should be used for the end fittings of a composite long-rod insulator from a specific manufacturer such as Lapp?

**Passages the answer cites:**

> [S1] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 22-23: To avoid damaging good insulators, tap them; do not hit them hard. (3) Repair. (a) If the main body of a pin type or post insulator is cracked, replace it immediately. (b) Hone small chips from shells or skirts, and paint with an insulating paint or varnish to provide a glossy finish and to lessen dirt accumulation. (c) Since the loss of a skirt on a pin-type insulator reduces the insulation value of the insulator by 30 percent or more, replace such broken units. b. Nonceramic insulators. Nonceramic or composite insulators include core, weathersheds, and metal-end fittings. A weathershed is the external part of the insulator that protects the core or mechanical load-bearing component and provides the wet electrical strength and leakage distance. The core consists of resin and glass fibers. The weathersheds are of polymeric materials such as epoxy resins or elastomers and normally contain inorganic fillers. Since the insulating qualities of insulators, and their ability to prevent flashovers, depend on preventing contamination buildup, cleaning frequencies will depend on the location.
>
> [S4] FIST 4-1B Maintenance Scheduling for Electrical Equipment (US Bureau of Reclamation, 2005), p. 79-80: Base and mounting Check for loose bolts and insecure or inadequate supporting structure. Ventilating louvers and air filters Clean and replace as needed. Buses, splices, and bolts Check bolts for manufacturer’s recommended torque. Insulators Check for chipped or broken porcelain, excessive dirt film, and tracking; clean as necessary; replace broken insulators; tighten base and cap bolts. Space heaters Verify operation or operate continuously to overcome thermostat malfunction. Main switch blades and contacts See that blades are properly seated in the contacts; operate the switch several times and see that blades are properly aligned to engage contacts; clean contact surfaces if corroded; lubricate; tighten bolts and screws. Continued Contact and hinge spring and shunts Check pressure springs in contact and hinge and replace, if not adequate; replace flexible shunts, if frayed. Blade latches and stops See that blade latches, where provided, are engaged; check latches for proper engaging and holding blade against opening force. See that stops are in place and tight. Arcing switch blades and contacts Do not lubricate.
>
> [S9] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 111-112: Checking for contact erosion and vacuum ground buses by wiping with a dry, clean cloth or by condition is made with the circuit breaker removed vacuuming. ‘- from its switchgear cubicle. (a) Close the circuit breaker and measure the spring plate overtravel. Consult the manufac- (d) Check tightness of accessible bolted bus joints by the calibrated wrench method. Refer to manufacturer recommendations for proper torque values. Also check alignment and contacts of primary disconnecting devices for abnormal wear or damage. Check for sulfide deposits and use a solvent, such as alcohol, for removal of these deposits. (e) After cleaning and adjusting, run insulation resistance tests to measure resistance to ground and compare with previous readings for any sign of weakening of the insulation system. Comparisons should be made using a common temperature and humidity base. (3) Miscellaneous checks. Check supporting devices such as protective relays and controls as covered in chapter 11 and as follows:
>

**Answer:**

I can't give you a torque value. None of the manuals in the knowledge base lists one for composite long-rod insulator end fittings, from Lapp or any other manufacturer, and I won't guess a number.

**What the manuals do cover:**
- TM 5-684 describes composite insulators only in general terms: a resin and glass-fibre core, polymer weathersheds and metal end fittings. It gives no installation or torque data [S1].
- Wherever torque comes up, the manuals send you to the manufacturer. Examples are "check bolts for manufacturer's recommended torque" for disconnect switch hardware [S4], and "refer to manufacturer recommendations for proper torque values" for bolted bus joints [S9].

**Where to find the value:**
- **Lapp Insulators' installation instructions or datasheet** for your exact catalogue number. Torque depends on the fitting type (clevis, tongue, ball/socket, Y-clevis), the bolt size and the material.
- **The hardware supplier's data** for the bolts and connecting fittings, if they don't come from Lapp.
- **Your utility's construction standards or work instructions.**

These are older US documents (1996–2005), not current European standards. If you work in Germany or the EU, the relevant references are product standards such as IEC 61109 / DIN EN 61109 for composite insulators and DIN EN 50341 for overhead lines. I don't have those in the knowledge base, so I can't quote them.

- your declined: 

## m_h20

**Question:** In a lighting circuit where the lights are wired one after another, what is the same for every light?

**Reference:** The current (series circuit); the voltage varies.

**Passages the answer cites:**

> [S1] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 86: Circuits exceeding 277 volts to ground, but not exceeding 600 volts, need to meet NEC pole and structure mounting height requirements. b. Series circuits. In a series circuit, all of the lamps are connected in series. The same current, therefore, flows through all the lamps and the voltage varies .The power is supplied through a constant-current transformer (regulator). These transformers are available to supply circuits rated 6.6, 15, or 20 amperes. The most common value of current used is 6.6 amperes and only 6.6 and 20 amperes are used for airfield lighting circuits. The lamps may be connected either directly to the series circuit or to insulating transformers connected to the series circuit. Most series airfield lighting circuits use insulating transformers. Series circuits may be installed as an open-loop, a closed-loop, or a combination of both. In the closed loop and combination systems the conductors are close together in numerous places so the circuit can be conveniently short-circuited when troubleshooting. Series circuit voltages range from 2,400 to 7,200 volts, in order to maintain the constant current.
>
> [S2] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 86: In the closed loop and combination systems the conductors are close together in numerous places so the circuit can be conveniently short-circuited when troubleshooting. Series circuit voltages range from 2,400 to 7,200 volts, in order to maintain the constant current. Therefore, series circuits must always be treated as medium-voltage circuits. nents. the ballast. A multiple type lighting system consists o f luminaires, mounting structures for luminaires, the control system to switch luminaires on and off, and the input circuit which provides the low voltage to operate the luminaires. Generally, some type of power transformer will provide input low voltage. Transformer requirements are provided in chapter 7. 6-5. lamp types. There are two types of lights used in outdoo r luminaires. These are filament types and gaseous conductive types. Filament lamps use the filament for conducting current. Gaseous conductive types use an ionized gas or vapor for the electron flow and are of the electric-discharge lamp type or fluorescent lamp type. -- The basic, most visible part of an exterior lighting system, is the combination of luminaire and lamp or lamp/ballast.
>
> [S3] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 91: Series plug cutouts. Cutouts are plug-type units used to disconnect a series light circuit or its constant current regulator. With the plug handle assembly removed and secured, maintenance personnel are ensured of protection. d. Film cutouts. Film cutouts or film disks operate automatically and are inserted in older lamp sockets to bypass failed lamps. Some circuits that have more than one lamp on an insulating transformer will use film cutouts to bypass a burned-out lamp and keep the other lamps supplied from that transformer operating. Because of their size and shape, they are sometimes referred to as “dimes.” When current no longer flows because of lamp failure or removal, full circuit voltage exists across the cutout film, which then ruptures, allowing the series circuit to be completed. A new film cutout of proper rating must be used whenever a faulty lamp is replaced. It is good practice to replace the cutouts whenever lamps are replaced under a group replacement program. Always screw the lamp into the socket before inserting the socket into the receptacle.
>
> [S5] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 86: Outside building-mounted lighting is considered interior lighting, if its sole purpose is to facilitate entrance into that building. ‘V Most lighting circuits will be of the multiple circuit type. Generally series circuits are used for only airfield lighting systems (except for very small airfields) to provide uniform brightness to all lights in a circuit. Some older streetlighting and protective lighting circuits may also be supplied from series circuits. a. Multiple circuits. Multiple circuits use constant-voltage single-phase inputs, usually of 120, 208, 240, 277, and 480 volts. The lights are connected in parallel. There are no code restrictions on the location of 120-volt lamps. When installed on buildings, circuits exceeding 120 volts, but no t exceeding 277 volts to ground, need to meet NEC requirements for their distance from windows, platforms, and fire escapes. Circuits exceeding 277 volts to ground, but not exceeding 600 volts, need to meet NEC pole and structure mounting height requirements. b. Series circuits. In a series circuit, all of the lamps are connected in series.
>

**Answer:**

**The current is the same for every light.** In a series lighting circuit, the same current flows through all the lamps, while the voltage varies [S1].

Some more detail from TM 5-684 (US Army, 1996):
- A constant-current transformer (regulator) powers the circuit. Common ratings are 6.6, 15 or 20 A. 6.6 A is the most common, and airfield circuits use only 6.6 or 20 A [S1].
- Series circuits are mainly used for airfield lighting because they give every light the same brightness. Some older street and security lighting also uses them [S5].
- **Safety:** These circuits run at about 2,400 to 7,200 V to keep the current constant, so always treat them as medium-voltage circuits [S1][S2].
- If a lamp fails, a film cutout bypasses it so the rest of the circuit stays lit. Put in a new cutout with the right rating whenever you replace a faulty lamp [S3].

By comparison, the more common "multiple" (parallel) circuits work the other way round: every light gets the same voltage [S5].

- your correctness: 
- your faithful: 

## m_h14

**Question:** How long should I wait after switching off a power factor correction bank before working on it?

**Reference:** At least 5 minutes, then short the terminals to ground and to each other.

**Passages the answer cites:**

> [S1] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 144: After capacitors are deenergized allow at least 5 minutes for discharge and then short the capacitor terminals to ground and to each other. These grounding provisions should remain until work on the installation is completed. Although most power capacitors have a discharge resistor installed to automatically discharge them after they are disconnected from the circuit, it is not advisable to depend entirely on such resistors for safety. The initial inspection should be made within 24 hours after energizing a new capacitor installation. This inspection should be made at a time of maximum circuit voltage, usually during the first period of light load on the circuit. In addition to visual observations, this inspection should include voltage and current readings to ensure that voltages and currents do not exceed capacitor rating limits. Operating kilovars (the sum of the fundamental frequency kilovars and any harmonic frequency kilovars) should not exceed 135 percent of the capacitor rating. Routine maintenance and inspection should be accomplished at least four times per year.
>
> [S2] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 144: Fixed shunt capacitors are used to improve the voltage level and switched shunt capacitors are used to improve voltage regulation. Capacitor installations will generally be connected grounded wye because of undesirable effects of other connections. All capacitor banks should be equipped with a means to disconnect them from the electric system. Some systems utilize ungrounded connections to minimize interference and because this connection is considered easy to fuse. Capacitors containing polychlorinated biphenyl (PCB) should have been disposed of under the procedures of the Environmental Protection Agency to implement the Toxic Substances Control Act of marked as containin g PCB’s. ANSI/IEEE 18 now requires an impregnant identification visible from the ground with a glue color used to designate a nonPCB liquid. Capacitors retain a charge after they ar e deenergized. After capacitors are deenergized allow at least 5 minutes for discharge and then short the capacitor terminals to ground and to each other. These grounding provisions should remain until work on the installation is completed.
>
> [S4] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 146-147: When an internal discharge resistor is present, however, the reading obtained will be that of the discharge resistor. This is much lower than the dielectri c resistance, which may also need to be obtained from the manufacturer. This testing will indicate whether the internal discharge resistor is operable . Remember, that the internal discharge device provided in a capacitor is not a substitute for the recommended practice of manually discharging the residual stored charge before working on a capacitor. (a) Procedure. With the capacitor unit insulated from ground, apply a voltage equal to twice rated voltage between case and terminals (all terminals connected together) in accordance with figure with the test circuit fused and containing sufficient impedance to limit the current, should the capacitor under test be shorted. b. Handbook tests. These are not standard industry tests, but have been recommended by facility engineers as a method of determining the capacitor \ FUSE AN0 FREQUENCY condition. Figure 13-1. Terminal-to-terminal voltage test circuit. / 1 MAXIMUM + CAP”uC$R / POWER SOURCE 1 RATED VOLTAGE 1. 1 CAPACITOR CASE INSUIA~EO Figure 13-2.
>
> [S5] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 104: Freeing of an iced switch mechanism may be assisted by a few sharp raps on the vertical operating pipe or suddenly applied tugs on the operating handle. (3) Operate power-operated switches periodically to ensure that their mechanisms and control features are functioning properly. If the circuit cannot be de-energized to operate a switch, the operating mechanism should be disengaged from the linkage. Check control circuits and mechanisms in the disengaged manner, unless disengagement will change the overall adjustment. b. Disconnecting switches: (1) Check that no load is being carried by the switch, prior to operating a disconnecting o r horngap switch. (2) Check to determine that operation does not remove necessary safety grounds, prior to opening a grounding switch. Check the circuit to confirm that it is not energized, prior to closing. (3) Operate disconnecting switches rapidly to reduce arcing time and possible burning of contacts. No workshould be done on switches until both sides of eac hphase are de-energized and properly grounded. In addition to the recommendations given herein, follow the specific maintenance directions of the switch manufacturer.
>

**Answer:**

**Wait at least 5 minutes after switching off the capacitor bank. Then short the capacitor terminals to ground and to each other before you touch anything** [S1][S2].

Key points from the manual (US Army TM 5-684):
- **Capacitors stay charged after they're switched off.** That's why you need the wait and then the manual shorting [S2].
- **Don't rely on the built-in discharge resistors.** Most power capacitors have one, but the manual says it's not advisable to depend entirely on it [S1]. The internal discharge device doesn't replace discharging the stored charge by hand [S4].
- **Leave the grounds on until all work on the installation is finished** [S1][S2].
- **Before working on the switches, both sides of every phase must be switched off and properly grounded** [S5].

This comes from a 1996 US Army manual, not current EU or German rules. If you work under DIN VDE 0105-100 / EN 50110 or similar local rules, those rules come first. So does the discharge time the capacitor maker gives on the nameplate or in the manual. Always check with a suitable voltage tester that the bank is dead before you apply the grounds.

- your correctness: 
- your faithful: 

## o03

**Question:** How often does the German transmission operator Amprion wash its insulators?

**Passages the answer cites:**

> [S1] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 66: (1) Facility procedures. Each facility should develop procedures based on their level of voltages, contaminants, and available equipment. Using advice from the local utility concerning their energized insulator washing practices is recommended. (2) Energized cleaning methods. Energized cleaning methods include the use of high pressure, medium-pressure,and low-pressure water; compressed air with abrasive dry cleaning compounds; and wiping with burlap cleaning hammocks using hot sticks. All of these procedures are covered in ANSI/IEEE 957. (3) Technical considerations of pressurized water cleaning. Certain items influence the effectiveness of pressurized water cleaning performance and the leakage current that can pass to the operator’s body from the water stream. These items are the nozzle conductor distance, the water’s resistivity, the water pressure, and the nozzle-orifice diameter. Wind can interfere with the efficiency of the water spray. The washing interval must be such as to avoid flashover accidents during hot-line washing, which can occur when the acceptable limit of contamination has been exceeded. Some points, covered in more detail in ANSI/IEEE 957, are as follows: (a) Water resistiuity .
>
> [S3] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 23: (1) Inspection. Look for fractures and any rust. (2) Repair insulators having defective hardware. a. Causes of contamination . All insulators and also bushings are designed to permit satisfactory operation with some contamination. However, alternate wetting by early morning mist and fog, followed by exposure to dust and wind, can build up harmful deposits. Special contamination problems are encountered near steel mills, cement and chemical plants, and other factories that saturate the air with finely divided, semi-conductive particles. Along coastal areas, salt deposits build up and materially reduce the flashover value. Many of these deposits are extremely tenacious, requiring that the insulator be removed from service and cleaned by hand. Where contamination is serious, specia l longleakage suspension insulators for high-voltage lines have been used; but, where severe deposits occur, washing of special insulators is required as often as for standard insulators. To lengthen maintenance intervals, in areas where contamination is severe, ceramic insulators and bushings may be coated with special silicone greases.
>
> [S4] TM 5-684 Facilities Engineering: Electrical Exterior Facilities (US Army, 1996), p. 65-66: (2) Insulators. The usual procedures in the replacement of insulators are as follows: - (a) Fasten the wire tongs to the conductor. (b) Remove the tie or clamp from the conductor. (c) Move the conductor clear of the work area and secure the wire tong. (d) Remove old insulator. (e) Mount new insulator. (f) Return conductor to insulator. (g) Tie or clamp conductor to insulator. (h) Remove wire tongs. (3) Crossarms: In replacing crossarms, apply steps (a), (b), an d (c) for all lines . Then remove crossarm and insulators and replace with ne w crossarm with new insulators in place. Then apply steps (f), (g), and (h). d. Washing energized insulators . Hand cleaning of de-energized insulators is described in chapter 3, section IV ANSI/IEEE 957 provides a guide for cleaning insulators. (1) Facility procedures. Each facility should develop procedures based on their level of voltages, contaminants, and available equipment. Using advice from the local utility concerning their energized insulator washing practices is recommended. (2) Energized cleaning methods.
>

**Answer:**

I can't answer that from my sources. My knowledge base has only older US federal manuals (US Army TM 5-684 from 1996 and US Bureau of Reclamation FIST volumes from 2000–2005). None of them mention Amprion or other German or EU utilities. For Amprion's actual practice, you'd need Amprion itself, its published maintenance or grid documentation, or the relevant DIN EN / IEC and VDE guidance.

**What the US manuals say about how often to wash insulators:**
- **No fixed interval.** Wash often enough that dirt never builds up past the safe limit. Going past that limit can cause a flashover (an arc across the insulator) during live-line washing [S1].
- **Each site sets its own schedule.** It depends on voltage level, the type of contamination and the equipment available, and the manual recommends asking the local utility how it washes energized insulators [S1][S4]. ANSI/IEEE 957 is the reference for the details [S1][S4].
- **Contamination drives frequency.** Washing is needed more often near steel mills, cement and chemical plants, and on coasts with salt build-up. In bad conditions, special long-leakage insulators still need washing as often as standard ones. Coating porcelain insulators with silicone grease can stretch the time between cleanings [S3].
- **Methods:** high-, medium- or low-pressure water, compressed air with dry abrasive cleaning compounds, or wiping by hand with tools on insulated poles [S1].

Treat this as general background only, not a description of how German transmission operators work.

- your declined: 
