/* BU FAYLNI ADOBE'DAN OLING — o'zimiz yozmaymiz.
 *
 * CSInterface.js — Adobe'ning rasmiy CEP kutubxonasi, panel bilan
 * Premiere (ExtendScript) orasidagi ko'prik. Uni Adobe'ning o'zi
 * tarqatadi va har CEP versiyasiga mosi bor.
 *
 * Qayerdan olish (CEP 11 uchun):
 *   https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_11.x/CSInterface.js
 *
 * Qadamlar:
 *   1. Yuqoridagi havolani oching
 *   2. «Raw» tugmasini bosib faylni yuklab oling
 *   3. AYNAN SHU faylning o'rniga qo'ying:
 *        client/js/CSInterface.js
 *
 * Bu placeholder o'rnida qolsa, panel ochilganda quyidagi xato chiqadi
 * va «Qo'llash» ishlamaydi.
 */
if (typeof CSInterface === "undefined") {
  window.__csinterface_yoq = true;
}
