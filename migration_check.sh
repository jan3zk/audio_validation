set -e

# # Example of a script call:
# sudo sh migration_check.sh -s FE-B-S**** -g Artur-B-G**** -r CJVT


while getopts s:g:r: flag
do
    case "${flag}" in
        s) snemalec=${OPTARG};;
        g) govorec=${OPTARG};;
        r) remote_name=${OPTARG};;
    esac
done

echo ""
echo "Preverjanje ujemanja števila posnetkov na Arturju:"

art_sou_bkp_dir="/storage/rsdo/cjvt/BraniGovor/BraniGovor-04-FE-IzvorniPosnetki-bkp/$snemalec/$govorec"
echo -n "$art_sou_bkp_dir: "
art_sou_bkp=`ls $art_sou_bkp_dir | wc -l`
echo $art_sou_bkp

art_acc_dir="/storage/rsdo/cjvt/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki/$snemalec/$govorec"
echo -n "$art_acc_dir: "
art_acc=`ls $art_acc_dir | wc -l`
echo $art_acc

art_acc_bkp_dir="/storage/rsdo/cjvt/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki-bkp/$snemalec/$govorec"
echo -n "$art_acc_bkp_dir: "
art_acc_bkp=`ls $art_acc_bkp_dir | wc -l`
echo $art_acc_bkp

art_rej_dir="/storage/rsdo/cjvt/BraniGovor/BraniGovor-04-FE-IzvorniPosnetki-bkp/$snemalec/ZavrnjeniPosnetki/$govorec"
echo -n "$art_rej_dir: "
art_rej=`ls $art_rej_dir | wc -l`
echo $art_rej

echo -n "#Artur:odobreni == #Artur:odobreni_bkp ... "
if [ $art_acc -eq $art_acc_bkp ];
then
  echo "OK"
else
  echo "ERR"
fi

echo -n "#Artur:izvorni_bkp - #Artur:odobreni == #Artur:zavrnjeni ... "
art_subtr="$((art_sou_bkp-art_acc))"
if [ $art_subtr -eq $art_rej ];
then
  echo "OK"
else
  echo "ERR"
fi

echo ""
echo "Preverjanje ujemanja števila posnetkov na nas.cjvt.si:"

nas_sou_bkp_dir="ASR/BraniGovor/BraniGovor-04-FE-IzvorniPosnetki-bkp/$snemalec/$govorec"
echo -n "nas.cjvt.si:$nas_sou_bkp_dir: "
nas_sou_bkp="$(rclone size $remote_name:$nas_sou_bkp_dir)"
nas_sou_bkp=`echo $nas_sou_bkp | sed 's@^[^0-9]*\([0-9]\+\).*@\1@'`
echo $nas_sou_bkp

nas_acc_dir="ASR/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki/$snemalec/$govorec"
echo -n "nas.cjvt.si:$nas_acc_dir: "
nas_acc="$(rclone size $remote_name:$nas_acc_dir)"
nas_acc=`echo $nas_acc | sed 's@^[^0-9]*\([0-9]\+\).*@\1@'`
echo $nas_acc

nas_acc_bkp_dir="ASR/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki-bkp/$snemalec/$govorec"
echo -n "nas.cjvt.si:$nas_acc_bkp_dir: "
nas_acc_bkp="$(rclone size $remote_name:$nas_acc_bkp_dir)"
nas_acc_bkp=`echo $nas_acc_bkp | sed 's@^[^0-9]*\([0-9]\+\).*@\1@'`
echo $nas_acc_bkp

nas_rej_dir="ASR/BraniGovor/BraniGovor-04-FE-IzvorniPosnetki-bkp/$snemalec/ZavrnjeniPosnetki/$govorec"
echo -n "nas.cjvt.si:$nas_rej_dir: "
nas_rej="$(rclone size $remote_name:$nas_rej_dir)"
nas_rej=`echo $nas_rej | sed 's@^[^0-9]*\([0-9]\+\).*@\1@'`
echo $nas_rej

echo -n "#nas:odobreni == #nas:odobreni_bkp ... "
if [ $nas_acc -eq $nas_acc_bkp ];
then
  echo "OK"
else
  echo "ERR"
fi

echo -n "#nas:izvorni_bkp - #nas:odobreni == #nas:zavrnjeni ... "
nas_subtr="$((nas_sou_bkp-nas_acc))"
if [ $nas_subtr -eq $nas_rej ];
then
  echo "OK"
else
  echo "ERR"
fi
