== To resolve ==
* License per image/expedition (<license> now a mixture of {{PD-Sweden-photo}} and {{cc-zero}})
* Only EM and VKM support archive links per below

== Refuse upload ==
* Images without <Fotograf>
* Image without <Beskrivning>

==Fixed for this upload==
<batch> = 2018-02
<museum> = VKM
<ext> = .tif

== Filename ==
<short info>_-_SMVK_-<Fotonummer>.<ext>

== Mapped ==
<museum> - Wikidata [manually mapped via museums.json]
<Fotograf> - Wikidata/Category/Creator
<Händelse> - Wikidata/Category/en/sv [manually mapped via expeditions.json]
<Personnamn, avbildad> - Wikidata/Category
<Motivord> - Category
<Sökord> - Category
<Land, Fotograferad> - Wikidata/Category [all must be mapped]
<Region, fotograferad i> - Wikidata/Category
<Ort fotograferad i> - Wikidata/Category
<Etnisk grupp> - Wikidata/Category

== Template ==
{{Photograph
 |photographer         =  <Fotograf:Creator>
 |title                =
 |description          = {{sv|<sv_description>}}
{{en|<en_description>}}
 |original description = <sv_description><br />
 ''Plats:'' <Geografiskt namn, annat><br />
 ''Etnisk grupp:'' <Etnisk grupp> (<Etn, tidigare>)<br />
 ''Nyckelord:'' <Motivord><br />
 ''Sökord:'' <Sökord>
 |depicted people      = <Personnamn, avbildad:Wikidata_(/-separated)>
 |depicted place       = <depicted place>
 |date                 = <Fotodatum:parsed>
 |medium               =
 |dimensions           =
 |institution          = {{Institution:Statens museer för världskultur}}
 |department           = {{Item|<museum:Wikidata>}}
 |references           = <Referens / Publicerad i>
 |object history       =
 |exhibition history   =
 |credit line          =
 |inscriptions         =
 |notes                =
Related archive card(s): <archive_card>
Id in other archives: <other_id>
 |accession number     = {{SMVK-<museum>-link|<Postnr.>|<Fotonummer>}}
 |source               = The original image file was received from SMVK with the following filename: '''<Fotonummer>.<ext>'''
{{SMVK cooperation project|museum=<museum>}}
 |permission           = <license>
 |other_versions       =
}}

== Categories ==
[[Category:<Händelse:Category>]]
[[Category:<Motivord:Category>]]
[[Category:<Sökord:Category>]]
[[Category:<Personnamn, avbildad:Category>]]
[[Category:<Ort fotograferad i:Category>]] OR [[Category:<Region, fotograferad i:Category>]] OR [[Category:<Land Fotograferad:Category>]]
[[Category:<Etnisk grupp:Category>]]
[[Category:Media contributed by SMVK <batch>]]

== Error categories ==
if <Fotodatum> not YYYY or YYYY-MM or YYYY-MM-DD: [[Category:Media contributed by SMVK with bad dates]]

== depicted place ==
if <Ort fotograferad i:Wikidata>:
{{city|<Ort fotograferad i:Wikidata>}}
elif <Region, fotograferad i:Wikiata>
<Ort fotograferad i>, {{city|<Region, fotograferad i:Wikiata>}}
else:
<Ort fotograferad i>, <Region, fotograferad i>, {{city|<Land, Fotograferad:Wikidata>}}

== archive_card ==
For each <Arkivkort_Id>:
"{{SMVK-<museum>-link|1=arkiv|2=<Arkivkort_Postnr>|3=<Arkivkort_Id>}}"

== other_id ==
For each <Objekt, externt / samma som>
If <Objekt, externt / samma som> starts with GNM:
{{GNM-link|<Objekt, externt / samma som:strip "GNM:">}}

== short_info ==
<Beskrivning>. <Ort fotograferad i>; <Land, Fotograferad>

== sv_description ==
<Beskrivning>. <Etnisk grupp>. <Ort fotograferad i>, <Region, fotograferad i>, <Land, Fotograferad:Wikidata>. <Händelse:sv>

== en_description ==
<Beskrivning, engelska>. {{Item|<Etnisk grupp:Wikidata>}}. <Händelse:en>
