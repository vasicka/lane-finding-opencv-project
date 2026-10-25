import os
import cv2
import numpy as np
import glob
import matplotlib.pyplot as plt

def PerspectiveTransform(img, src, dst):
    # Primena perspektivne transformacije
    matrix = cv2.getPerspectiveTransform(np.float32(src), np.float32(dst))
    warped = cv2.warpPerspective(img, matrix, (img.shape[1], img.shape[0]))
    return warped

def process_frame(frame, camera_matrix, dist_coeffs, src, dst):
    # Uklanjanje distorzije
    undistorted_img = cv2.undistort(frame, camera_matrix, dist_coeffs, None, camera_matrix)
    
    # Detekcija ivica i binarizacija
    gray = cv2.cvtColor(undistorted_img, cv2.COLOR_BGR2GRAY)
    low_threshold = 300
    high_threshold = 400
    canny_edges = cv2.Canny(gray, low_threshold, high_threshold)

    lab = cv2.cvtColor(undistorted_img, cv2.COLOR_BGR2LAB)
    b_channel = lab[:, :, 2]
    b_thresh_min = 150
    b_thresh_max = 255
    binary_b = np.zeros_like(b_channel)
    binary_b[(b_channel >= b_thresh_min) & (b_channel <= b_thresh_max)] = 1

    combined_binary = np.zeros_like(binary_b)
    combined_binary[(binary_b == 1) | (canny_edges > 0)] = 1  
    binary_img = combined_binary * 255

    # Perspektivna transformacija
    img_pt = PerspectiveTransform(binary_img, src, dst)

    # Detekcija traka i fitting
    nonzero_y, nonzero_x = np.nonzero(img_pt)
    histogram = np.sum(img_pt[img_pt.shape[0] // 2:, :], axis=0)
    midpoint = int(histogram.shape[0] // 2)
    left_base = np.argmax(histogram[:midpoint])
    right_base = np.argmax(histogram[midpoint:]) + midpoint

    window_height = 80
    margin = 100
    minpix = 50

    left_lane_inds = []
    right_lane_inds = []

    for window in range(0, img_pt.shape[0], window_height):
        win_y_low = window
        win_y_high = window + window_height
        win_xleft_low = left_base - margin
        win_xleft_high = left_base + margin
        win_xright_low = right_base - margin
        win_xright_high = right_base + margin

        good_left_inds = ((nonzero_x >= win_xleft_low) & (nonzero_x <= win_xleft_high) & (nonzero_y >= win_y_low) & (nonzero_y < win_y_high)).nonzero()[0]
        good_right_inds = ((nonzero_x >= win_xright_low) & (nonzero_x <= win_xright_high) & (nonzero_y >= win_y_low) & (nonzero_y < win_y_high)).nonzero()[0]

        left_lane_inds.append(good_left_inds)
        right_lane_inds.append(good_right_inds)
        
        if len(good_left_inds) > minpix:
            left_base = int(np.mean(nonzero_x[good_left_inds]))
        if len(good_right_inds) > minpix:
            right_base = int(np.mean(nonzero_x[good_right_inds]))

    left_lane_inds = np.concatenate(left_lane_inds)
    right_lane_inds = np.concatenate(right_lane_inds)

    leftx = nonzero_x[left_lane_inds]
    lefty = nonzero_y[left_lane_inds]
    rightx = nonzero_x[right_lane_inds]
    righty = nonzero_y[right_lane_inds]

    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)

    ploty = np.linspace(0, img_pt.shape[0] - 1, img_pt.shape[0])
    left_fitx = left_fit[0] * ploty**2 + left_fit[1] * ploty + left_fit[2]
    right_fitx = right_fit[0] * ploty**2 + right_fit[1] * ploty + right_fit[2]

    ym_per_pix = 30 / 720
    xm_per_pix = 3.7 / 700
    y_eval = np.max(ploty)
    left_fit_cr = np.polyfit(ploty * ym_per_pix, left_fitx * xm_per_pix, 2)
    right_fit_cr = np.polyfit(ploty * ym_per_pix, right_fitx * xm_per_pix, 2)
    left_curverad = ((1 + (2 * left_fit_cr[0] * y_eval * ym_per_pix + left_fit_cr[1])**2)**1.5) / np.abs(2 * left_fit_cr[0])
    right_curverad = ((1 + (2 * right_fit_cr[0] * y_eval * ym_per_pix + right_fit_cr[1])**2)**1.5) / np.abs(2 * right_fit_cr[0])
    avg_curverad = (left_curverad + right_curverad) / 2

    car_position = img_pt.shape[1] / 2
    lane_center = (left_fitx[-1] + right_fitx[-1]) / 2
    center_offset = (car_position - lane_center) * xm_per_pix

    warp_zero = np.zeros_like(img_pt).astype(np.uint8)
    color_warp = np.dstack((warp_zero, warp_zero, warp_zero))

    pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
    pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
    pts = np.hstack((pts_left, pts_right))
    cv2.fillPoly(color_warp, np.int_([pts]), (0, 255, 0))

    newwarp = PerspectiveTransform(color_warp, dst, src)
    result = cv2.addWeighted(undistorted_img, 1, newwarp, 0.3, 0)

    cv2.putText(result, f"Radius: {avg_curverad:.2f}m", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(result, f"Vehicle offset: {center_offset:.2f}m", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return result

def main():
    #***************************Compute the camera calibration matrix and distortion coefficients given a set of chessboard images************************

    os.makedirs('output_images', exist_ok=True)  # folder za izlazne slike

    chessboard_corners = (9, 6)  # Broj unutrasnjih uglova sahovske table(S obzirom da imamo kvadrata 10x7, uglova imamo 10x6)

    # Najpre napravimo trodimenzijalnu matricu 54 elementa ispunjenu nulama, a zatim zamenimo to sa koordinatama uglova, Z osa ostaje na 0
    matrix = np.zeros((chessboard_corners[0] * chessboard_corners[1], 3), np.float32)
    matrix[:, :2] = np.mgrid[0:chessboard_corners[0], 0:chessboard_corners[1]].T.reshape(-1, 2)

    matrix_points = []  # 3D tacke sahovske table 
    image_points = []  # koordinate uglova detektovanih na slikama

    images = glob.glob('camera_cal/*.jpg')  # Putanja do foldera sa slikama, uzimamo sve slike iz foldera

    for image in images:
        img = cv2.imread(image)  # Učitavanje slike
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Konvertujemo sliku u sivu, kako bi se detektovale ivice na slici naspram svetline

        # Pronalazimo sve uglove na slici, ukoliko uspesno pronadje 54 ugla sahovske table, ret ce biti TRUE, a u corners smestamo koordinate uglova na slici
        ret, corners = cv2.findChessboardCorners(gray, chessboard_corners, None) #ako zelimo poseban nacin detektovanja, to mozemo zameniti umesto None

        if ret:
            matrix_points.append(matrix)  # Dodajemo trodimenzijalne tacke sahovske table
            image_points.append(corners)  # Dodajemo koordinate uglova na slici


    # Sada mozemo da izracunamo kalibracione parametre
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(matrix_points, image_points, gray.shape[::-1], None, None)
    print("/**************** Camera Matrix ****************/")
    print(camera_matrix)

    print("\n/*************** Distortion Coefficients *****************/")
    print(dist_coeffs)

    # Snimamo primer sahovske table pre i posle uklanjanja distorzije
    chess_img = cv2.imread('camera_cal/calibration1.jpg')
    chess_undist = cv2.undistort(chess_img, camera_matrix, dist_coeffs, None, camera_matrix)
    cv2.imwrite('output_images/0_undistort_chessboard.jpg', np.hstack((chess_img, chess_undist)))


    #*************************** Apply a distortion correction to raw images ************************************

    # Sada mozemo da ispravimo iskrivljene slike
    img = cv2.imread('test_images/whiteCarLaneSwitch.jpg') 
    undistorted_img = cv2.undistort(img, camera_matrix, dist_coeffs, None, camera_matrix)
    cv2.imwrite('output_images/1_undistorted.jpg', undistorted_img)
    # cv2.imshow('Distorted image: ', img)
    # cv2.imshow('Undistorted image: ', undistorted_img)
    # cv2.waitKey(0) #slike ce ostati prikazane sve dok ih rucno ne uklonimo
    # cv2.destroyAllWindows()

    #************************** Use color transforms, gradients, etc., to create a thresholded binary image ************************************

    # Koristicemo Canny algoritam za detekciju linija na putu
    gray = cv2.cvtColor(undistorted_img, cv2.COLOR_BGR2GRAY)  # To cemo mnogo lakse uraditi sa slikom u nijansama sive boje, jer se tako lakse detektuje promena inteziteta piksela
    low_threshold = 300  # Donji prag za Canny (sto je nizi detektujemo vise ivica ali se dobija i vise suma)
    high_threshold = 400  # Gornji prag za Canny ( sto je visi, manje ivica ali i manje suma)
    canny_edges = cv2.Canny(gray, low_threshold, high_threshold) #primena Canny algoritma

    # LAB color space i pragiranje B kanala - ovo radimo kako bismo detektovali i zute linije na putu
    lab = cv2.cvtColor(undistorted_img, cv2.COLOR_BGR2LAB) # konvertovanje u LAB color space
    b_channel = lab[:, :, 2]  # Samo B kanal! (zato sto on predstavlja nijansu zuta-plava)
    b_thresh_min = 150
    b_thresh_max = 255 #ovo su vrednosti prilagodjenje za zutu boju
    binary_b = np.zeros_like(b_channel) #najpre pravimo crnu sliku velicine kao b_channel
    binary_b[(b_channel >= b_thresh_min) & (b_channel <= b_thresh_max)] = 1 #sada primenjujemo nase tresholde na B kanal 

    # Kombinujemo rezultate kako bismo dobili precizniju detekciju, i za zute i za bele linije
    combined_binary = np.zeros_like(binary_b)
    combined_binary[(binary_b == 1) | (canny_edges > 0)] = 1  
    binary_img = combined_binary * 255
    cv2.imwrite('output_images/2_combined_binary.jpg', binary_img)
    # Prikaz rezultata
    cv2.imshow('Combined Binary', combined_binary * 255) #mnozimo sa 255 jer ce crni deo (0) i dalje ostati 0, a sivi deo(1) ce postati 255 odnosno beo za imshow
    cv2.waitKey(0)
    cv2.destroyAllWindows()


    #*************************** Apply a perspective transform to rectify binary image ("birds-eye view") ************************************

    line_dst_offset = 150  # Veci offset - sira perspektiva
    src = [  #koordinate 4 tacke sa ulazne slike 
        [440, 340],  #gornje tacke
        [530, 340],  #gornje tacke
        [850, 530], #donje tacke 
        [190, 530]   #donje tacke
    ]

    dst = [  # tacke na novoj slici, pomeramo ih tako da prethodno odabrani pravougaonik sada predstavlja citavu sliku
        [src[3][0] + line_dst_offset, 0],                
        [src[2][0] - line_dst_offset, 0],                  
        [src[2][0] - line_dst_offset, binary_img.shape[0]], 
        [src[3][0] + line_dst_offset, binary_img.shape[0]]  
    ]

    img_pt = PerspectiveTransform(binary_img, src, dst)
    cv2.imwrite('output_images/3_perspective_transform.jpg', img_pt)
    cv2.imshow('PerspectiveTransform image', img_pt)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


    # ************************* Detect lane pixels and fit to find the lane boundary. *************************

    
    nonzero_y, nonzero_x = np.nonzero(img_pt) # Pronalazimo sve bele piksele na binarnoj slici, odnosno delove traka (povratna vrednost su x i y kooordinate belih piksela)

    #izracunavamo histogram kako bismo pronasli pocetne pozicije leve i desne trake
    histogram = np.sum(img_pt[img_pt.shape[0] // 2:, :], axis=0)
    midpoint = int(histogram.shape[0] // 2)
    left_base = np.argmax(histogram[:midpoint])
    right_base = np.argmax(histogram[midpoint:]) + midpoint


    # implementacija kliznog prozora
    window_height = 80
    margin = 100
    minpix = 50

    left_lane_inds = []
    right_lane_inds = []

    # Priprema slike za iscrtavanje prozora
    output_img = np.dstack((img_pt, img_pt, img_pt)) * 255
    
    # iteracija kroz klizne prozore
    for window in range(0, img_pt.shape[0], window_height):
        #definisanje granica prozora
        win_y_low = window
        win_y_high = window + window_height
        win_xleft_low = left_base - margin
        win_xleft_high = left_base + margin
        win_xright_low = right_base - margin
        win_xright_high = right_base + margin

        # Iscrtavanje prozora na slici
        cv2.rectangle(output_img, (win_xleft_low, win_y_low), (win_xleft_high, win_y_high), (0, 255, 0), 2)
        cv2.rectangle(output_img, (win_xright_low, win_y_low), (win_xright_high, win_y_high), (0, 255, 0), 2)
        #pronalazak piksela unutar slike
        good_left_inds = ((nonzero_x >= win_xleft_low) & (nonzero_x <= win_xleft_high) & (nonzero_y >= win_y_low) & (nonzero_y < win_y_high)).nonzero()[0]
        good_right_inds = ((nonzero_x >= win_xright_low) & (nonzero_x <= win_xright_high) & (nonzero_y >= win_y_low) & (nonzero_y < win_y_high)).nonzero()[0]

        left_lane_inds.append(good_left_inds)
        right_lane_inds.append(good_right_inds)
        
        #azuriranje pozicije prozora
        if len(good_left_inds) > minpix:
            left_base = int(np.mean(nonzero_x[good_left_inds]))
        if len(good_right_inds) > minpix:
            right_base = int(np.mean(nonzero_x[good_right_inds]))

    left_lane_inds = np.concatenate(left_lane_inds)
    right_lane_inds = np.concatenate(right_lane_inds)

    leftx = nonzero_x[left_lane_inds]
    lefty = nonzero_y[left_lane_inds]
    rightx = nonzero_x[right_lane_inds]
    righty = nonzero_y[right_lane_inds]

    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)

    ploty = np.linspace(0, img_pt.shape[0] - 1, img_pt.shape[0])
    left_fitx = left_fit[0] * ploty**2 + left_fit[1] * ploty + left_fit[2]
    right_fitx = right_fit[0] * ploty**2 + right_fit[1] * ploty + right_fit[2]

    # Iscrtavanje pronadjenih piksela i polinoma
    output_img[nonzero_y[left_lane_inds], nonzero_x[left_lane_inds]] = [255, 0, 0]
    output_img[nonzero_y[right_lane_inds], nonzero_x[right_lane_inds]] = [0, 0, 255]

    for i in range(len(ploty)):
        if 0 <= int(left_fitx[i]) < img_pt.shape[1]:
            cv2.circle(output_img, (int(left_fitx[i]), int(ploty[i])), 2, (255, 255, 0), -1)
        if 0 <= int(right_fitx[i]) < img_pt.shape[1]:
            cv2.circle(output_img, (int(right_fitx[i]), int(ploty[i])), 2, (255, 255, 0), -1)

    # Prikaz slike sa rezultatima
    plt.imshow(output_img)
    plt.title("Lane Detection and Fitted Polynomials")
    plt.savefig('output_images/4_lane_detection.png')  # mora pre plt.show()
    plt.show()

    
# ****************************** Determine the curvature of the lane and vehicle position with respect to center. ***************************

    # Pretvaranje u realne jedinice
    ym_per_pix = 30 / 720  # metara po pikselu u vertikalnom smeru (30m - priblizna duzina traka sa testnih slika)
    xm_per_pix = 3.7 / 700  # metara po pikselu u horizontalnom smeru (3.7m - priblizna sirina traka)

    # Racunamo radijus zakrivljenosti leve i desne trake i prosecni radijus
    y_eval = np.max(ploty)
    left_fit_cr = np.polyfit(ploty * ym_per_pix, left_fitx * xm_per_pix, 2)
    right_fit_cr = np.polyfit(ploty * ym_per_pix, right_fitx * xm_per_pix, 2)
    left_curverad = ((1 + (2 * left_fit_cr[0] * y_eval * ym_per_pix + left_fit_cr[1])**2)**1.5) / np.abs(2 * left_fit_cr[0]) #radijus zakrivljenosti leve trake
    right_curverad = ((1 + (2 * right_fit_cr[0] * y_eval * ym_per_pix + right_fit_cr[1])**2)**1.5) / np.abs(2 * right_fit_cr[0]) #radijus zakrivljenosti desne trake
    avg_curverad = (left_curverad + right_curverad) / 2  #sto je radijus veci, put je ravniji

    # Odredjujemo poziciju vozila u odnosu na centar trake
    car_position = img_pt.shape[1] / 2
    lane_center = (left_fitx[-1] + right_fitx[-1]) / 2
    center_offset = (car_position - lane_center) * xm_per_pix #ako je negativan vozilo je pomereno u levo, a ako je pozitivan u desno

    # ****************************** Warp the detected lane boundaries back onto the original image. *******************************
    
    # ****************************** Output visual display of the lane boundaries and numerical estimation of lane curvature and vehicle position. *******************************

    warp_zero = np.zeros_like(img_pt).astype(np.uint8) #kreiramo crnu sliku i pretvaramo podatke u tip uint8 
    color_warp = np.dstack((warp_zero, warp_zero, warp_zero)) # R G B - u pocetku prazna slika



    # Definisanje tacaka koji ce biti iscrtane
    pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
    pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))]) 
    pts = np.hstack((pts_left, pts_right)) #Pravi zatvoren prabougaonik izmedju traka
    cv2.fillPoly(color_warp, np.int_([pts]), (0, 255, 0)) #iscrtavanje zelenom bojoms

    newwarp = PerspectiveTransform(color_warp, dst, src) # vracamo iz pticije u osnovnu perspektivu
    result = cv2.addWeighted(undistorted_img, 1, newwarp, 0.3, 0) #kombinujemo originalnu sliku sa ispravljenom distorzijom i deo sa iscrtanom trakom

    # Ispisivanje zakrivljenosti i pozicije vozila na rezultujućoj slici
    cv2.putText(result, f"Radius: {avg_curverad:.2f}m", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1) #gornji levi ugao, belom bojom, velicina fonta 0.5 i debljine 1
    cv2.putText(result, f"Vehicle offset: {center_offset:.2f}m", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.imwrite('output_images/5_result.jpg', result)

    # Prikaz koncane slike
    cv2.imshow('Result', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Obrada videa
    video_path = 'test_videos/project_video01.mp4'
    cap = cv2.VideoCapture(video_path)

    out = cv2.VideoWriter('output_video.avi', cv2.VideoWriter_fourcc(*'XVID'), 20.0, (int(cap.get(3)), int(cap.get(4))))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        processed_frame = process_frame(frame, camera_matrix, dist_coeffs, src, dst)
        out.write(processed_frame)

        cv2.imshow('Processed Video', processed_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()

