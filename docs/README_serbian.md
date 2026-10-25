## Writeup Template

### You use this file as a template for your writeup.

---

**Lane Finding Project**

The goals / steps of this project are the following:

* Compute the camera calibration matrix and distortion coefficients given a set of chessboard images.
* Apply a distortion correction to raw images.
* Use color transforms, gradients, etc., to create a thresholded binary image.
* Apply a perspective transform to rectify binary image ("birds-eye view").
* Detect lane pixels and fit to find the lane boundary.
* Determine the curvature of the lane and vehicle position with respect to center.
* Warp the detected lane boundaries back onto the original image.
* Output visual display of the lane boundaries and numerical estimation of lane curvature and vehicle position.

[//]: # (Image References)

[image1]: ./examples/undistort_output.png "Undistorted"
[image2]: ./test_images/test1.jpg "Road Transformed"
[image3]: ./examples/binary_combo_example.jpg "Binary Example"
[image4]: ./examples/warped_straight_lines.jpg "Warp Example"
[image5]: ./examples/color_fit_lines.jpg "Fit Visual"
[image6]: ./examples/example_output.jpg "Output"
[video1]: ./project_video.mp4 "Video"

---

### Writeup / README

#### 1. Provide a Writeup that includes all the rubric points and how you addressed each one.

You're reading it!

### Camera Calibration

#### 1. Briefly state how you computed the camera matrix and distortion coefficients. Provide an example of a distortion corrected calibration image.

Kod za kalibraciju kamere se nalazi u funkciji `main()`, (linije 115-153).

Za kalibraciju se koriste slike sahovske table iz foldera `camera_cal/`. Tabla ima 10x7 kvadrata, odnosno 9x6 unutrasnjih uglova, pa je `chessboard_corners = (9, 6)`.

Najpre se pravi niz `matrix` sa 3D koordinatama uglova table u realnom vremenu, oblika (0,0,0), (1,0,0), (2,0,0) ... (8,5,0). Pretpostavlja se da je tabla ravna i da lezi u ravni z = 0, pa su ove koordinate iste za svaku sliku.

Zatim se za svaku sliku iz `camera_cal/`:
1. slika ucita i pretvori u nijanse sive (`cv2.cvtColor`),
2. pomocu `cv2.findChessboardCorners` pronadju uglovi table,
3. ako su svi uglovi uspesno pronadjeni, 3D tacke (`matrix`) se dodaju u listu `matrix_points`, a pronadjene 2D koordinate uglova na slici u listu `image_points`.

Kada su prikupljene tacke sa svih slika, poziva se `cv2.calibrateCamera(matrix_points, image_points, ...)`, koja vraca matricu kamere (`camera_matrix`) i koeficijente distorzije (`dist_coeffs`). 
Da bi se proverila kalibracija, na sliku `camera_cal/calibration1.jpg` primenjena je funkcija `cv2.undistort` sa dobijenim parametrima. Levo je originalna slika, a desno slika sa uklonjenom distorzijom. Na originalnoj slici linije table su savijene ka ivicama, a na ispravljenoj su prave:

![Calibration Original and Undistorted](../output_images/0_undistort_chessboard.jpg)


### Pipeline (single images)

#### 1. Provide an example of a distortion-corrected image.

Ovaj deo koda se nalazi u funkciji `main()`, (linije 156-161).

Kada sam dobila matricu kamere (`camera_matrix`) i koeficijente distorzije (`dist_coeffs`) iz kalibracije, iskoristila sam ih da ispravim sliku puta. Ucitala sam test sliku `test_images/whiteCarLaneSwitch.jpg` i nad njom pozvala funkciju `cv2.undistort` sa ta dva parametra. Dobijena slika `undistorted_img` se zatim koristi u svim sledecim koracima (binarizacija, perspektivna transformacija i detekcija traka).

Razlika izmedju originalne i ispravljene slike puta nije toliko uocljiva kao kod sahovske table, ali se najvise primecuje na ivicama slike, gde je distorzija najveca.
Originalna slika puta:

![Original Road Image](../test_images/whiteCarLaneSwitch.jpg)

Primer slike puta nakon uklanjanja distorzije:

![Undistorted Road Image](../output_images/1_undistorted.jpg)



#### 2. Describe how (and identify where in your code) you used color transforms, gradients or other methods to create a thresholded binary image.  Provide an example of a binary image result.

Ovaj deo koda se nalazi u funkciji `main()`, (linije 167-187).

Za dobijanje binarne slike kombinovala sam dve metode: detekciju ivica (gradijent) pomocu Canny algoritma i pragiranje boje u LAB color space-u.

**1. Canny detekcija ivica**

Sliku bez distorzije (`undistorted_img`) sam najpre pretvorila u nijanse sive, jer se tako lakse detektuje promena intenziteta piksela. Zatim sam primenila `cv2.Canny` sa donjim pragom 300 i gornjim pragom 400. Pragove sam postavila relativno visoko, da bi se izdvojile samo jake ivice (linije na putu), a da bude sto manje suma. Canny dobro pronalazi bele linije, jer se one jasno razlikuju od tamnog asfalta.

**2. LAB color space - B kanal**

Zute linije se slabije vide na sivoj slici, pa sam ih posebno izdvojila preko boje. Sliku sam pretvorila u LAB color space (`cv2.COLOR_BGR2LAB`) i uzela samo B kanal, jer on predstavlja odnos zute i plave boje. Na B kanalu sam primenila prag od 150 do 255, tako da pikseli u tom opsegu (zuta boja) dobijaju vrednost 1, a svi ostali 0. Rezultat je slika `binary_b`.

**3. Kombinovanje**

Na kraju sam spojila oba rezultata: piksel u slici `combined_binary` ima vrednost 1 ako je pronadjen Canny algoritmom ili ako pripada zutoj boji iz B kanala. Tako se na jednoj slici dobijaju i bele i zute linije. Za prikaz i snimanje slika se mnozi sa 255, da bi pikseli sa vrednoscu 1 postali beli.

Primer binarne slike (zuta linija levo je dobijena iz B kanala, a bele isprekidane linije desno pomocu Canny algoritma):

![Combined Binary Image](../output_images/2_combined_binary.jpg)



#### 3. Describe how (and identify where in your code) you performed a perspective transform and provide an example of a transformed image.

Sama transformacija je u funkciji `PerspectiveTransform()` (linije 7-11), a izbor tacaka i njen poziv su u funkciji `main()` (linije 194-212).

Funkcija `PerspectiveTransform(img, src, dst)` prima sliku i dva skupa od po 4 tacke. Pomocu `cv2.getPerspectiveTransform` racuna matricu transformacije koja tacke `src` preslikava u tacke `dst`, a zatim pomocu `cv2.warpPerspective` primenjuje tu matricu na celu sliku. Izlazna slika je iste velicine kao ulazna.

Tacke `src` sam izabrala rucno na slici puta, tako da obuhvataju trapez oko trake ispred vozila: dve gornje tacke su blizu horizonta, a dve donje pri dnu slike. Tacke `dst` cine pravougaonik, tako da trapez sa ulazne slike postane pravougaonik koji se proteze celom visinom slike. Za pomeranje tacaka po x osi koristila sam `line_dst_offset = 150`, da bi trake na transformisanoj slici bile malo udaljene od ivica pravougaonika.

Transformaciju sam primenila na binarnu sliku iz prethodnog koraka (`binary_img`) i dobila sliku iz pticije perspektive (`img_pt`). Da su tacke dobro izabrane vidi se po tome sto su leva i desna traka na transformisanoj slici priblizno vertikalne i paralelne.

Ista funkcija se kasnije koristi i za vracanje u originalnu perspektivu, samo sa zamenjenim redosledom tacaka (`dst`, `src`).
Ulazna binarna slika:

![Binary Image](../output_images/2_combined_binary.jpg)

Primer binarne slike nakon perspektivne transformacije:

![Perspective Transform Image](../output_images/3_perspective_transform.jpg)



#### 4. Describe how (and identify where in your code) you identified lane-line pixels and fit their positions with a polynomial?

Ovaj deo koda se nalazi u funkciji `main()`, (linije 218-296).

Za detekciju piksela traka koristila sam binarnu sliku iz pticije perspektive (`img_pt`) i metodu kliznih prozora (sliding windows).

Najpre sam pomocu `np.nonzero` pronasla koordinate svih belih piksela. Pocetne pozicije traka (`left_base` i `right_base`) odredila sam pomocu histograma donje polovine slike, kao maksimume u levoj i desnoj polovini.

Zatim sam sliku po visini podelila na prozore od 80 piksela. Za svaki prozor se oko pozicije trake uzima pravougaonik sirine 2 x 100 piksela (`margin = 100`) i cuvaju se svi beli pikseli unutar njega. Ako je pronadjeno vise od 50 piksela (`minpix = 50`), sledeci prozor se pomera na njihovu srednju x vrednost, pa prozori prate traku i kada je zakrivljena.

Kroz pronadjene piksele leve i desne trake sam pomocu `np.polyfit` provukla polinom drugog reda oblika x = A * y^2 + B * y + C. Polinom je x(y) jer su trake na slici skoro vertikalne.

Na slici su zelenom bojom prikazani klizni prozori, crvenom pikseli leve trake, plavom pikseli desne trake, a zutom dobijeni polinomi:

![Lane Detection and Fitted Polynomials](../output_images/4_lane_detection.png)



#### 5. Describe how (and identify where in your code) you calculated the radius of curvature of the lane and the position of the vehicle with respect to center.

Ovaj deo koda se nalazi u funkciji `main()`, (linije 299-316).

Da bi rezultati bili u metrima, a ne u pikselima, koristila sam sledece odnose:
- `ym_per_pix = 30 / 720` - metara po pikselu u vertikalnom smeru (posmatrani deo puta je dugacak priblizno 30 m),
- `xm_per_pix = 3.7 / 700` - metara po pikselu u horizontalnom smeru (sirina trake je priblizno 3.7 m).

**Radijus zakrivljenosti**

Koordinate traka (`left_fitx`, `right_fitx`, `ploty`) sam pomnozila ovim odnosima i ponovo pomocu `np.polyfit` provukla polinom drugog reda, ovaj put u metrima. Radijus sam izracunala po formuli:

R = (1 + (2 * A * y + B)^2)^(3/2) / |2 * A|

gde su A i B koeficijenti polinoma, a y je dno slike (`y_eval`), odnosno mesto najblize vozilu. Radijus sam racunala posebno za levu i desnu traku, a kao konacan rezultat uzela njihovu srednju vrednost (`avg_curverad`). Sto je radijus veci, put je ravniji.

**Pozicija vozila**

Pretpostavka je da je kamera postavljena na sredini vozila, pa je pozicija vozila sredina slike (`car_position`). Centar trake (`lane_center`) sam izracunala kao srednju vrednost x koordinata leve i desne trake na dnu slike. Razliku ove dve vrednosti sam pomnozila sa `xm_per_pix` i dobila odstupanje vozila od centra trake u metrima (`center_offset`). Ako je vrednost negativna, vozilo je pomereno ulevo, a ako je pozitivna, udesno.

Za test sliku dobijeni su radijus od priblizno 2204 m i odstupanje od -0.20 m. Ove vrednosti se ispisuju na konacnoj slici.



#### 6. Provide an example image of your result plotted back down onto the road such that the lane area is identified clearly.

Ovaj deo koda se nalazi u funkciji `main()`, (linije 318-340).

Najpre sam napravila praznu crnu sliku iste velicine kao slika iz pticije perspektive (`color_warp`). Od tacaka leve trake (`left_fitx`, `ploty`) i desne trake u obrnutom redosledu napravila sam zatvoren poligon izmedju traka i obojila ga zelenom bojom pomocu `cv2.fillPoly`.

Ovu sliku sam zatim vratila u originalnu perspektivu pomocu iste funkcije `PerspectiveTransform()`, samo sa zamenjenim tackama (`dst`, `src`). Dobijenu sliku (`newwarp`) sam pomocu `cv2.addWeighted` spojila sa slikom bez distorzije, tako da zelena povrsina bude providna i da se ispod nje vidi put.

Na kraju sam pomocu `cv2.putText` u gornjem levom uglu ispisala radijus zakrivljenosti i odstupanje vozila od centra trake.

Konacan rezultat za test sliku:

![Result Image](../output_images/5_result.jpg)



### Pipeline (video)

#### 1. Provide a link to your final video output.  Your pipeline should perform reasonably well on the entire project video (wobbly lines are ok but no catastrophic failures that would cause the car to drive off the road!).

Obrada videa se nalazi na kraju funkcije `main()`, (linije 347-367), a obrada pojedinacnog frejma u funkciji `process_frame()` (linije 13-112).

Za obradu videa napravila sam funkciju `process_frame()`, koja nad jednim frejmom radi iste korake kao i za test sliku: uklanjanje distorzije, binarizaciju (Canny + B kanal), perspektivnu transformaciju, detekciju traka kliznim prozorima, racunanje radijusa i pozicije vozila i iscrtavanje trake na frejmu. Pri tome se koriste isti parametri kalibracije i iste `src` i `dst` tacke kao za test sliku.

Video `test_videos/project_video01.mp4` sam ucitala pomocu `cv2.VideoCapture` i u petlji obradila svaki frejm funkcijom `process_frame()`. Obradjeni frejmovi se upisuju u novi video pomocu `cv2.VideoWriter` i istovremeno prikazuju na ekranu. Obrada se moze prekinuti pritiskom na taster `q`.

Pipeline radi dobro na celom videu (svih 221 frejmova): traka je prepoznata u svakom frejmu i zelena povrsina prati traku bez vecih odstupanja.

Video je na lokaciji: [Output Video](../output_video.avi)


### Discussion

#### 1. Briefly discuss any problems / issues you faced in your implementation of this project.  Where will your pipeline likely fail?  What could you do to make it more robust?

U ovom projektu pipeline verovatno ne bi radio dobro kod senki, promene osvetljenja i ostrih krivina, jer Canny hvata i ivice koje nisu trake, a `src` tacke su fiksne i prilagodjene ovom videu. Takodje, svaki frejm se obradjuje nezavisno, pa ako se u nekom frejmu ne pronadju pikseli trake, program bi se prekinuo.

Ovaj projekat bi trebalo unaprediti kako bi radio i na test videima sa vise suma. Kada razmisljam o mogucim promenama, za detekciju ivica u realnom vremenu mozda bi bolji izbor bio Sobel operator, jer je brzi od Canny algoritma. Sa druge strane, Canny daje preciznije ivice, pa bi trebalo pronaci pravu meru izmedju brzine i preciznosti. Pored toga, rezultat bi bio stabilniji kada bi se polinomi usrednjavali kroz nekoliko uzastopnih frejmova.
