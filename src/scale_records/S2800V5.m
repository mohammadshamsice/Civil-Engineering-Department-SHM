% پارامترهای لرزه‌ای ساختگاه تهران (ورودی‌ها را با نقشه‌های پیوست ۱ تطبیق دهید)
Ss = 1.35;  
S1 = 0.6;  

% بردارهای مرجع اختصاصی برای خاک تیپ III (جداول ۱-۲ و ۲-۲)
Ss_ref = [0.5, 0.75, 1.0, 1.25, 1.5];
Fs_ref = [1.3, 1.2, 1.1, 1.0, 1.0]; 

S1_ref = [0.2, 0.3, 0.4, 0.5, 0.6];
F1_ref = [2.2, 2.1, 2.1, 2.1, 2.1]; 

% محاسبه خودکار ضرایب سایت با درون‌یابی خطی
if Ss >= 1.5
    Fs = 1.0;
elseif Ss <= 0.5
    Fs = 1.3;
else
    Fs = interp1(Ss_ref, Fs_ref, Ss, 'linear');
end

if S1 >= 0.6
    F1 = 2.1;
elseif S1 <= 0.2
    F1 = 2.2;
else
    F1 = interp1(S1_ref, F1_ref, S1, 'linear');
end

% محاسبه مقادیر شتاب طیفی بیشینه
Sms = Fs * Ss; 
Sm1 = F1 * S1; 

% محاسبه مقادیر شتاب طیفی طرح
Sds = (2/3) * Sms; 
Sd1 = (2/3) * Sm1; 

% محاسبه زمان‌های تناوب کلیدی
T0 = 0.2 * (Sd1 / Sds); 
Ts = Sd1 / Sds; 
TL = 6.0; 

% تعریف بردار زمان تناوب با گام دقیق 0.05 ثانیه تا 6 ثانیه
T = 0:0.01:6;
Sa = zeros(size(T));

% محاسبه طیف استاندارد
for i = 1:length(T)
    t = T(i);
    if t >= 0 && t < T0
        Sa(i) = Sds * (0.4 + 0.6 * (t / T0));
    elseif t >= T0 && t <= Ts
        Sa(i) = Sds;
    elseif t > Ts && t <= TL
        Sa(i) = Sd1 / t;
    elseif t > TL
        Sa(i) = Sd1 * (TL / (t^2));
    end
end

% رسم نمودار با استایل مینیمال 
figure;
plot(T, Sa, 'r', 'LineWidth', 1.5);

% لیبل‌های انگلیسی
xlabel('Period, T (s)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('Design Spectral Acceleration, S_a (g)', 'FontSize', 12, 'FontWeight', 'bold');
title(sprintf('Standard Design Response Spectrum - Soil Type III\n(S_s=%.2f, S_1=%.2f)', Ss, S1), 'FontSize', 14);

% تنظیمات گرافیکی
set(gca, 'Box', 'off', 'TickDir', 'out', 'TickLength', [.015 .015], ...
    'XMinorTick', 'on', 'YMinorTick', 'on', 'LineWidth', 1.2);

% ذخیره داده‌ها در فایل متنی (.txt) با اعداد رند
export_data = [T', Sa']; 
filename = 'Design_Spectrum_Data.txt';
writematrix(export_data, filename, 'Delimiter', 'tab');

disp(['Data successfully exported up to 6 seconds to: ', filename]);