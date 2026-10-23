"""Build the GM bestiary from bestiary.json. Requires reportlab and Cyrillic fonts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
W, H = A4
M = 39
CW = W - 2 * M
INK = colors.HexColor('#242B30')
MUTED = colors.HexColor('#59656B')
ACCENT = colors.HexColor('#783C3C')
LINE = colors.HexColor('#D6DADD')
PALE = colors.HexColor('#F1F3F3')
GOLD = colors.HexColor('#986C30')


def normalize(value):
    if isinstance(value, str):
        return value.replace('\u2014', '-').replace('\u2013', '-').replace('\u2011', '-').replace('\u2022', '/')
    if isinstance(value, list):
        return [normalize(x) for x in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    return value


def fonts(font_dir=None):
    candidates = [Path(font_dir)] if font_dir else []
    candidates.extend([Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts', Path('/usr/share/fonts/truetype/dejavu')])
    for base in candidates:
        if (base / 'arial.ttf').exists():
            files = ['arial.ttf', 'arialbd.ttf', 'ariali.ttf', 'arialbi.ttf']
            title = base / 'georgia.ttf'
            break
        if (base / 'DejaVuSans.ttf').exists():
            files = ['DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans-Oblique.ttf', 'DejaVuSans-BoldOblique.ttf']
            title = base / 'DejaVuSerif.ttf'
            break
    else:
        raise RuntimeError('No Cyrillic fonts found. Pass --font-dir with Arial or DejaVu fonts.')
    for name, file in zip(['Body', 'Body-Bold', 'Body-Italic', 'Body-BoldItalic'], files):
        pdfmetrics.registerFont(TTFont(name, str(base / file)))
    pdfmetrics.registerFontFamily('Body', normal='Body', bold='Body-Bold', italic='Body-Italic', boldItalic='Body-BoldItalic')
    pdfmetrics.registerFont(TTFont('Title', str(title if title.exists() else base / files[0])))


def style(size=10, leading=None, color=INK, align=TA_LEFT, font='Body'):
    return ParagraphStyle('text', fontName=font, fontSize=size, leading=leading or size * 1.31, textColor=color, alignment=align)


def p(text, size=10, **kwargs):
    return Paragraph(text, style(size, **kwargs))


def draw_p(c, text, x, y, width, size=10, **kwargs):
    para = p(text, size, **kwargs)
    _, height = para.wrap(width, 2000)
    para.drawOn(c, x, y - height)
    return y - height


def footer(c, page, label):
    c.setStrokeColor(LINE)
    c.line(M, 34, W-M, 34)
    c.setFont('Body', 7.4)
    c.setFillColor(MUTED)
    c.drawString(M, 22, 'ЭТНА / СПРАВОЧНИК МАСТЕРА')
    c.drawRightString(W-M, 22, f'{label} / {page:02d}')
    if page > 1:
        c.linkRect('', 'encounters', (M, 17, M+190, 31), relative=0, thickness=0)


def running(c, label):
    c.setFont('Body-Bold', 7.5)
    c.setFillColor(ACCENT)
    c.drawString(M, H-33, 'ИСЧАДИЯ СОПРЯЖЕНИЙ')
    c.setFillColor(MUTED)
    c.drawRightString(W-M, H-33, label)
    c.setStrokeColor(LINE)
    c.line(M, H-41, W-M, H-41)


def overview(c, data):
    c.bookmarkPage('encounters')
    c.addOutlineEntry('Таблица рекомендуемых встреч', 'encounters', 0)
    y = H-47
    y = draw_p(c, 'ПОЛЕВОЙ БЕСТИАРИЙ ОХОТНИКОВ ЭТНЫ', M, y, CW, 8.3, color=ACCENT, font='Body-Bold')-18
    y = draw_p(c, 'Исчадия<br/>Сопряжений', M, y, CW, 35, leading=39, font='Title')-12
    y = draw_p(c, escape(data['party']), M, y, CW, 11, color=MUTED)-9
    y = draw_p(c, 'D&amp;D 2024 / Авторские правила / Только для мастера', M, y, CW, 8.5, color=MUTED)-18
    budgets = Table([[p('НИЗКАЯ', 7.5, color=MUTED), p('СРЕДНЯЯ', 7.5, color=MUTED), p('ВЫСОКАЯ', 7.5, color=MUTED)],
                     [p('4 500 опыта', 15, font='Body-Bold'), p('7 800 опыта', 15, font='Body-Bold'), p('10 200 опыта', 15, font='Body-Bold')]], colWidths=[CW/3]*3)
    budgets.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE), ('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,0),9),('BOTTOMPADDING',(0,1),(-1,1),10)]))
    _, bh = budgets.wrap(CW, 500)
    budgets.drawOn(c, M, y-bh)
    y -= bh+20
    y = draw_p(c, 'Рекомендуемые встречи', M, y, CW, 17, font='Title')-9
    rows = [[p(x, 8.2, color=colors.white, font='Body-Bold') for x in ['СОСТАВ', 'ОПЫТ', 'КЛЮЧ К ПОБЕДЕ', 'СТР']]]
    for i, monster in enumerate(data['creatures'], 1):
        rows.append([p(f'<link href="#creature-{i}" color="#242B30"><b>{escape(monster["name"])}</b></link><br/>{escape(monster["encounter"])}', 8.6),
                     p(f'{monster["xp"]:,}'.replace(',', ' ')+ ('*' if i==4 else ''), 9), p(escape(monster['weak']), 8.6),
                     p(f'<link href="#creature-{i}" color="#783C3C"><b>{i+2:02d}</b></link>', 10, align=TA_CENTER)])
    table=Table(rows, colWidths=[196,57,CW-196-57-33,33])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),ACCENT),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,-1),(-1,-1),0.5,LINE)]))
    _, th=table.wrap(CW,1000)
    table.drawOn(c,M,y-th)
    y-=th+12
    y=draw_p(c, '* Разрыв: награда за закрытие источника, а не оценка ПО. Все встречи рассчитаны как отдельные серьёзные столкновения.',M,y,CW,8.3,color=MUTED)-7
    y=draw_p(c, 'Названия и номера страниц кликабельны. Закладки PDF открывают каждое существо; ссылка в нижнем колонтитуле возвращает к этой таблице.',M,y,CW,8.3,color=MUTED)
    if y < 48:
        raise RuntimeError(f'Overview overflow: bottom={y}')
    footer(c,1,'НАВИГАЦИЯ')
    c.showPage()


def rules(c):
    c.bookmarkPage('rules')
    c.addOutlineEntry('Памятка мастеру и общие правила','rules',0)
    running(c,'ПЕРЕД ИГРОЙ')
    y=draw_p(c,'Памятка мастеру',M,H-59,CW,25,font='Title')-18
    blocks=[
        ('Как читать статблоки',[
            ('Обозначения','КД - класс доспеха; Сл - сложность; БМ - бонус мастерства. Расстояния в футах. Неуказанные спасброски равны модификатору характеристики. Неуказанных сопротивлений и иммунитетов нет.'),
            ('Перезарядка 5-6','После использования бросайте к6 в начале каждого хода существа: на 5-6 способность восстанавливается. В начале встречи она доступна.'),
            ('Захват','Освобождение: действие и проверка Силы (Атлетика) или Ловкости (Акробатика) против указанной Сл. Также действуют общие правила окончания захвата.'),
            ('Легендарные действия','Не более одного сразу после окончания чужого хода. Все применения восстанавливаются в начале хода монстра. Недееспособный монстр использовать их не может.'),
            ('Тип существ','«Исчадия» - термин охотников. Игровой тип этих существ - Аберрация. Способности исключительно против Fiend на них не действуют.')]),
        ('Подготовить честный вызов',[
            ('Доступные слабости','Если у персонажей есть книга охотников, содержащиеся в ней сведения известны без проверки. Проверки нужны для новых подробностей: якорей, шлюзов, механизмов.'),
            ('Показать угрозу','Крик, трещины пола и область кошмара имеют заметные признаки и границы. Игроки получают ход на ответ. Сохраняй подсказки даже при особенно сильной партии.'),
            ('Два способа решения','Заклинание холода или руна; огненная атака или жаровня; силовое поле или молот. Подготовка помогает, а окружение оставляет решение другой партии.'),
            ('Перемещение','Принудительное перемещение прекращается перед сплошной преградой. Столкнуть с уступа можно; дополнительного урона от самого перемещения нет без прямого указания способности.')]),
        ('Баланс под вашу партию',[
            ('Бюджет','Опыт врагов складывается без множителей за количество. Для шести героев 7-го уровня: 4 500 / 7 800 / 10 200 опыта. Предложенные встречи близки к высокому бюджету.'),
            ('Оценка сложности','ПО авторские и предварительные. Предполагаются магическое оружие, хорошие защитные предметы и заклинания 4-го круга. Статблоки не прошли игровой плейтест.'),
            ('Очень высокий урон','Если партия обычно наносит 180-200 урона за раунд, перед игрой увеличь хиты одиночного босса примерно на 20%, сохранив КД и Сл. Для стай сначала используй указанное количество.'),
            ('Несколько боёв','Это отдельные серьёзные встречи. Серия без отдыха требует меньшего числа врагов или более мягкого окружения. Эффекты цепей, рун, воды и прочего ниже - авторские свойства этих встреч.')]),
    ]
    for heading, entries in blocks:
        y=draw_p(c,escape(heading),M,y,CW,13.2,color=ACCENT,font='Body-Bold')-7
        for title, body in entries:
            y=draw_p(c,f'<b>{escape(title)}.</b> {escape(body)}',M,y,CW,9.9)-5.5
        y-=10
    y=draw_p(c,'Источники и редакция',M,y,CW,11,color=ACCENT,font='Body-Bold')-5
    refs='Основа лора: приложенный пользователем текст охотников Этны. Авторская механика: согласованный в чате бестиарий. Редакция от 23 октября 2026. Теневики остаются необязательной трактовкой слухов.'
    y=draw_p(c,escape(refs),M,y,CW,8.2,color=MUTED)-5
    for title,url in [('Правила построения встреч','https://www.dndbeyond.com/sources/dnd/br-2024/dms-toolbox#CombatEncounterDifficulty'),('Глоссарий D&D 2024','https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary/'),('Статблоки и легендарные действия','https://www.dndbeyond.com/sources/dnd/br-2024/creature-stat-blocks/')]:
        y=draw_p(c,f'<link href="{url}" color="#783C3C">{escape(title)}</link>',M,y,CW,8.2)-3
    if y < 48:
        raise RuntimeError(f'Rules overflow: bottom={y}')
    footer(c,2,'ПАМЯТКА')
    c.showPage()


def blocks_for(monster, size):
    groups=[]
    for heading, entries in monster['sections']:
        for j,(title,body) in enumerate(entries):
            group=[]
            if j==0:
                group.append((p(escape(heading),11.1,color=ACCENT,font='Body-Bold'),5,True))
            group.append((p(f'<b>{escape(title)}.</b> {escape(body)}',size),5,False))
            groups.append(group)
    for j,(title,body) in enumerate(monster['gm']):
        group=[]
        if j==0:
            group.append((p('Окружение и противодействие',11.1,color=ACCENT,font='Body-Bold'),5,True))
        group.append((p(f'<b>{escape(title)}.</b> {escape(body)}',size),5,False))
        groups.append(group)
    return groups


def group_height(group,width):
    return sum(item.wrap(width,2000)[1]+gap for item,gap,_ in group)


def monster_page(c,monster,i):
    c.bookmarkPage(f'creature-{i}')
    c.addOutlineEntry(monster['name'],f'creature-{i}',0)
    running(c,f'{i:02d} / 10')
    y=draw_p(c,escape(monster['name']),M,H-58,CW,24 if len(monster['name'])<27 else 21,font='Title')-5
    y=draw_p(c,escape(monster['kind']),M,y,CW,9.3,color=MUTED)-5
    y=draw_p(c,escape(monster['role']),M,y,CW,8.2,color=ACCENT,font='Body-Bold')-11
    fields=[('КД',monster['ac']),('ИНИЦИАТИВА',monster['init']),('ХИТЫ',monster['hp']),('СКОРОСТЬ',monster['speed'])]
    stats=Table([[p(f'<font size="7.2" color="#59656B">{lab}</font><br/><b>{escape(val)}</b>',10) for lab,val in fields]],colWidths=[CW*0.22,CW*0.17,CW*0.25,CW*0.36])
    stats.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    _,sh=stats.wrap(CW,1000)
    stats.drawOn(c,M,y-sh)
    y-=sh+9
    names=['СИЛ','ЛОВ','ТЕЛ','ИНТ','МДР','ХАР']
    cells=[]
    for lab,val in zip(names,monster['abilities']):
        mod=(val-10)//2
        cells.append(p(f'<font size="7.2" color="#59656B">{lab}</font><br/><b>{val}</b> ({mod:+d})',11,align=TA_CENTER))
    ability=Table([cells],colWidths=[CW/6]*6)
    ability.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,-1),0.5,LINE),('LINEBELOW',(0,0),(-1,-1),0.5,LINE),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    _,ah=ability.wrap(CW,1000)
    ability.drawOn(c,M,y-ah)
    y-=ah+8
    detail_width=(CW-20)/2
    details=[p(f'<b>{escape(lab)}:</b> {escape(val)}',8.8,leading=11.2) for lab,val in monster['details']]
    dh=[item.wrap(detail_width,1000)[1]+2 for item in details]
    detail_split=min(range(1,len(details)),key=lambda k:max(sum(dh[:k]),sum(dh[k:])))
    for dx,items in [(M,details[:detail_split]),(M+detail_width+20,details[detail_split:])]:
        dy=y
        for item in items:
            _,ih=item.wrap(detail_width,1000)
            item.drawOn(c,dx,dy-ih)
            dy-=ih+2
    y-=max(sum(dh[:detail_split]),sum(dh[detail_split:]))
    y-=10
    box_h=45
    bottom=58+box_h
    available=y-bottom
    gutter=20
    chosen=None
    for size in [10.1,10.0,9.9,9.8,9.7,9.6,9.5,9.4]:
        groups=blocks_for(monster,size)
        for ratio in [0.5,0.52,0.48,0.54,0.46,0.56,0.44]:
            left=(CW-gutter)*ratio
            right=CW-gutter-left
            options=[]
            for split in range(1,len(groups)):
                lh=sum(group_height(g,left) for g in groups[:split])
                rh=sum(group_height(g,right) for g in groups[split:])
                options.append((max(lh,rh),abs(lh-rh),split))
            best=min(options)
            if best[0] <= available:
                chosen=(size,groups,best[2],best[0],left,right)
                break
        if chosen:
            break
    if chosen is None:
        raise RuntimeError(f'{monster["name"]}: content overflow; available {available:.1f}, need {best[0]:.1f}')
    size,groups,split,height,left,right=chosen
    for x,col,items in [(M,left,groups[:split]),(M+left+gutter,right,groups[split:])]:
        cy=y
        for group in items:
            for item,gap,is_heading in group:
                _,ih=item.wrap(col,2000)
                item.drawOn(c,x,cy-ih)
                cy-=ih+gap
        if cy<bottom-0.1:
            raise RuntimeError('Column overflow')
    c.setStrokeColor(LINE)
    c.line(M+left+gutter/2,bottom,M+left+gutter/2,y)
    c.setFillColor(PALE)
    c.roundRect(M,48,CW,box_h,4,stroke=0,fill=1)
    exp=f'{monster["xp"]:,}'.replace(',',' ')
    if i==4:
        exp+=' за цель'
    draw_p(c,f'<b>ВСТРЕЧА:</b> {escape(monster["encounter"])} / <b>{exp} опыта</b>',M+10,83,CW-20,9.1)
    draw_p(c,escape(monster['note']),M+10,68,CW-20,8.3,color=MUTED)
    footer(c,i+2,monster['name'].upper())
    c.showPage()
    return {'page':i+2,'name':monster['name'],'body_font':size,'column_height':round(height,2),'available':round(available,2)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'output'/'pdf'/'Исчадия Сопряжений - бестиарий мастера.pdf')
    parser.add_argument('--font-dir')
    args=parser.parse_args()
    fonts(args.font_dir)
    data=normalize(json.loads((HERE/'bestiary.json').read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(args.output),pagesize=A4,pageCompression=1,invariant=1)
    c.setTitle(data['title']+' - бестиарий мастера')
    c.setAuthor('Материалы кампании Bladen / охотники Этны')
    c.setSubject('D&D 2024: 10 авторских существ, окружение, рекомендуемые встречи')
    c.setViewerPreference('DisplayDocTitle','true')
    overview(c,data)
    rules(c)
    report=[monster_page(c,m,i) for i,m in enumerate(data['creatures'],1)]
    c.save()
    print(json.dumps({'pdf':str(args.output),'pages':12,'layout':report},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
