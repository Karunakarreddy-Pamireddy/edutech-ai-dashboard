"""
PDF Report Generator - Day 13
Generates a professional structured PDF report.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

BLUE       = colors.HexColor('#2F5496')
BLUE_DARK  = colors.HexColor('#1a3a6e')
BLUE_LIGHT = colors.HexColor('#e8f0fb')
GREEN      = colors.HexColor('#27ae60')
RED        = colors.HexColor('#c0392b')
ORANGE     = colors.HexColor('#e67e22')
PURPLE     = colors.HexColor('#8e44ad')
GREY       = colors.HexColor('#f0f4f8')
MUTED      = colors.HexColor('#777777')
WHITE      = colors.white
BLACK      = colors.HexColor('#222222')


def _styles():
    return {
        'title':    ParagraphStyle('title',    fontSize=22, textColor=WHITE,   fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4),
        'subtitle': ParagraphStyle('subtitle', fontSize=11, textColor=WHITE,   fontName='Helvetica',      alignment=TA_CENTER, spaceAfter=4),
        'meta':     ParagraphStyle('meta',     fontSize=9,  textColor=colors.HexColor('#c8d8f0'), fontName='Helvetica', alignment=TA_CENTER),
        'h1':       ParagraphStyle('h1',       fontSize=14, textColor=BLUE_DARK,fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=5),
        'h2':       ParagraphStyle('h2',       fontSize=11, textColor=BLUE,    fontName='Helvetica-Bold', spaceBefore=8,  spaceAfter=4),
        'body':     ParagraphStyle('body',     fontSize=9,  textColor=BLACK,   fontName='Helvetica',      spaceAfter=3, leading=13),
        'bold':     ParagraphStyle('bold',     fontSize=9,  textColor=BLACK,   fontName='Helvetica-Bold', spaceAfter=3),
        'finding':  ParagraphStyle('finding',  fontSize=22, textColor=GREEN,   fontName='Helvetica-Bold', alignment=TA_CENTER),
        'small':    ParagraphStyle('small',    fontSize=7.5,textColor=MUTED,   fontName='Helvetica-Oblique', spaceAfter=2),
    }


def _ts(hdr=BLUE, alt=GREY):
    return TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), hdr),
        ('TEXTCOLOR',     (0,0), (-1,0), WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0), 9),
        ('ALIGN',         (0,0), (-1,0), 'CENTER'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, alt]),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 8.5),
        ('ALIGN',         (1,1), (-1,-1), 'CENTER'),
        ('ALIGN',         (0,1), (0,-1), 'LEFT'),
        ('GRID',          (0,0), (-1,-1), 0.4, colors.HexColor('#d0d9e6')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
    ])


def generate_pdf_report(kpi_data: dict, pipeline_data: dict, model_data: dict = None) -> bytes:
    buf = io.BytesIO()
    W   = A4[0] - 4*cm
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
        title="EduTech Impact on AI — Analytics Report")
    S   = _styles()
    now = datetime.now().strftime("%d %B %Y, %H:%M")
    ov  = kpi_data.get('overview', {})
    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    def banner(rows_data, bg):
        t = Table(rows_data, colWidths=[W])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),
            ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
            ('LEFTPADDING',(0,0),(-1,-1),18),('RIGHTPADDING',(0,0),(-1,-1),18)]))
        return t

    story.append(banner([[Paragraph("EduTech Impact on AI", S['title'])]], BLUE_DARK))
    story.append(banner([
        [Paragraph("Student Performance Analytics Dashboard", S['subtitle'])],
        [Paragraph("Full-Stack Data Analytics + AI Project", S['subtitle'])],
        [Paragraph(f"Report generated: {now}", S['meta'])],
    ], BLUE))
    story.append(Spacer(1, 16))

    # Key finding box
    ai_boost = ov.get('ai_score_boost', 0)
    finding_t = Table([
        [Paragraph("KEY RESEARCH FINDING", S['bold'])],
        [Paragraph(f"+{ai_boost} pts", S['finding'])],
        [Paragraph(f"Students using AI study tools score an average of <b>{ai_boost} points higher</b> than those who don't.", S['body'])],
    ], colWidths=[W])
    finding_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),BLUE_LIGHT),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),
    ]))
    story.append(finding_t)
    story.append(Spacer(1, 18))

    # ── 1. Executive Summary ───────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", S['h1']))
    story.append(HRFlowable(width=W, thickness=1.5, color=BLUE, spaceAfter=7))
    kpi_rows = [
        ['Metric', 'Value', 'Metric', 'Value'],
        ['Total Records',    str(ov.get('total_records','—')), 'Avg Score',        str(ov.get('avg_score','—'))],
        ['Total Students',   str(ov.get('total_students','—')),'Pass Rate',        f"{ov.get('pass_rate_pct','—')}%"],
        ['AI Adoption',      f"{ov.get('ai_adoption_pct','—')}%",'AI Score Boost', f"+{ov.get('ai_score_boost','—')} pts"],
        ['AI Users Avg',     str(ov.get('avg_score_ai','—')), 'Non-AI Avg',       str(ov.get('avg_score_non_ai','—'))],
    ]
    kt = Table(kpi_rows, colWidths=[W*0.30, W*0.20, W*0.30, W*0.20])
    kts = _ts()
    kts.add('TEXTCOLOR',(3,3),(3,3),GREEN); kts.add('FONTNAME',(3,3),(3,3),'Helvetica-Bold')
    kts.add('TEXTCOLOR',(1,4),(1,4),GREEN); kts.add('TEXTCOLOR',(3,4),(3,4),RED)
    kts.add('FONTNAME',(1,4),(1,4),'Helvetica-Bold'); kts.add('FONTNAME',(3,4),(3,4),'Helvetica-Bold')
    kt.setStyle(kts)
    story.append(kt)
    story.append(Spacer(1, 14))

    # ── 2. AI vs Non-AI ────────────────────────────────────────────────────────
    story.append(Paragraph("2. AI vs Non-AI Score Analysis", S['h1']))
    story.append(HRFlowable(width=W, thickness=1.5, color=BLUE, spaceAfter=7))
    ai_data  = kpi_data.get('ai_vs_nonai', {})
    overall  = ai_data.get('overall', [])
    if overall:
        story.append(Paragraph("Overall Comparison", S['h2']))
        rows = [['Group','Avg Score','Count','Std Dev']]
        for g in overall:
            rows.append([g.get('ai_group',''), str(g.get('avg_score','')), str(g.get('count','')), str(g.get('std',''))])
        t = Table(rows, colWidths=[W*0.36,W*0.22,W*0.22,W*0.20]); t.setStyle(_ts()); story.append(t)
        story.append(Spacer(1, 9))
    by_subj = ai_data.get('by_subject', {})
    if by_subj and by_subj.get('subjects'):
        story.append(Paragraph("By Subject", S['h2']))
        rows = [['Subject','AI Avg','Non-AI Avg','AI Advantage']]
        for s, a, n in zip(by_subj['subjects'], by_subj['ai_scores'], by_subj['non_ai_scores']):
            d = round(a-n, 2)
            rows.append([s, str(a), str(n), f"+{d}" if d>=0 else str(d)])
        t = Table(rows, colWidths=[W*0.34,W*0.22,W*0.22,W*0.22])
        ts2 = _ts()
        for i in range(1,len(rows)):
            v = float(rows[i][3].replace('+',''))
            ts2.add('TEXTCOLOR',(3,i),(3,i), GREEN if v>=0 else RED)
            ts2.add('FONTNAME',(3,i),(3,i),'Helvetica-Bold')
        t.setStyle(ts2); story.append(t)
        story.append(Spacer(1, 14))

    # ── 3. Performance Breakdown ───────────────────────────────────────────────
    story.append(Paragraph("3. Performance Breakdown", S['h1']))
    story.append(HRFlowable(width=W, thickness=1.5, color=BLUE, spaceAfter=7))
    for title, key in [("By Subject","by_subject"),("By Class","by_class")]:
        d = kpi_data.get(key,{})
        if d and d.get('labels'):
            story.append(Paragraph(title, S['h2']))
            rows = [['Name','Avg Score','Count']]
            for lb, sc, ct in zip(d['labels'],d['scores'],d['counts']):
                rows.append([lb, str(sc), str(ct)])
            t = Table(rows, colWidths=[W*0.50,W*0.25,W*0.25]); t.setStyle(_ts()); story.append(t)
            story.append(Spacer(1, 9))
    dist = kpi_data.get('score_distribution',{})
    if dist and dist.get('labels'):
        story.append(Paragraph("Score Distribution", S['h2']))
        rows = [['Score Band','Count']]
        for lb, ct in zip(dist['labels'],dist['counts']): rows.append([lb, str(ct)])
        t = Table(rows, colWidths=[W*0.55,W*0.45]); t.setStyle(_ts()); story.append(t)

    # ── 4. Leaderboard ─────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("4. Student Leaderboard", S['h1']))
    story.append(HRFlowable(width=W, thickness=1.5, color=BLUE, spaceAfter=7))
    lb = kpi_data.get('leaderboard',{})
    medals = ['1st','2nd','3rd','4th','5th']
    if lb.get('top'):
        story.append(Paragraph("Top 5 Students", S['h2']))
        rows = [['Rank','Student ID','Avg Score','AI Tool']]
        for i,s in enumerate(lb['top']): rows.append([medals[i],s['student_id'],str(s['avg_score']),'Yes' if s['ai_used'] else 'No'])
        t = Table(rows, colWidths=[W*0.15,W*0.35,W*0.25,W*0.25]); t.setStyle(_ts(GREEN)); story.append(t)
        story.append(Spacer(1, 9))
    if lb.get('bottom'):
        story.append(Paragraph("Bottom 5 — Need Support", S['h2']))
        rows = [['Rank','Student ID','Avg Score','AI Tool']]
        for i,s in enumerate(lb['bottom']): rows.append([str(i+1),s['student_id'],str(s['avg_score']),'Yes' if s['ai_used'] else 'No'])
        t = Table(rows, colWidths=[W*0.15,W*0.35,W*0.25,W*0.25]); t.setStyle(_ts(RED)); story.append(t)
        story.append(Spacer(1, 14))

    # ── 5. Pipeline Health ─────────────────────────────────────────────────────
    story.append(Paragraph("5. Data Pipeline Health", S['h1']))
    story.append(HRFlowable(width=W, thickness=1.5, color=BLUE, spaceAfter=7))
    if pipeline_data and not pipeline_data.get('error'):
        ss = pipeline_data.get('score_stats',{}); au = pipeline_data.get('ai_tool_usage',{}); dr = pipeline_data.get('date_range',{})
        rows = [['Metric','Value'],
            ['Total Records', str(pipeline_data.get('total_records','—'))],
            ['Mean Score', str(ss.get('mean','—'))],
            ['Score Range', f"{ss.get('min','—')} – {ss.get('max','—')}"],
            ['AI Users', str(au.get('users','—'))],
            ['Non-AI Users', str(au.get('non_users','—'))],
            ['AI Adoption', f"{au.get('adoption_pct','—')}%"],
            ['Pass Rate', f"{pipeline_data.get('pass_rate_pct','—')}%"],
            ['Outliers Flagged', str(pipeline_data.get('outliers_flagged','—'))],
            ['Date Range', f"{dr.get('from','—')} to {dr.get('to','—')}"],
        ]
        t = Table(rows, colWidths=[W*0.55,W*0.45]); t.setStyle(_ts()); story.append(t)
        story.append(Spacer(1, 14))

    # ── 6. ML Model ────────────────────────────────────────────────────────────
    if model_data and model_data.get('trained'):
        story.append(Paragraph("6. AI Predictive Model Results", S['h1']))
        story.append(HRFlowable(width=W, thickness=1.5, color=BLUE, spaceAfter=7))
        m = model_data.get('meta',{})
        rows = [['Metric','Value'],
            ['Algorithm','Linear Regression (scikit-learn)'],
            ['Trained on', f"{m.get('trained_on','—')} records"],
            ['Train / Test Split', f"{m.get('train_size','—')} / {m.get('test_size','—')}"],
            ['R² Score', str(m.get('r2','—'))],
            ['MAE', f"{m.get('mae','—')} points"],
            ['RMSE', f"{m.get('rmse','—')} points"],
        ]
        t = Table(rows, colWidths=[W*0.55,W*0.45]); t.setStyle(_ts(PURPLE)); story.append(t)
        story.append(Spacer(1, 8))
        coefs = m.get('coefficients',{})
        if coefs:
            story.append(Paragraph("Feature Coefficients", S['h2']))
            rows = [['Feature','Coefficient']]
            for feat,val in sorted(coefs.items(),key=lambda x:abs(x[1]),reverse=True):
                rows.append([feat, f"+{val}" if val>=0 else str(val)])
            t = Table(rows, colWidths=[W*0.60,W*0.40])
            ts3 = _ts()
            for i in range(1,len(rows)):
                v = float(rows[i][1].replace('+',''))
                ts3.add('TEXTCOLOR',(1,i),(1,i),GREEN if v>=0 else RED)
                ts3.add('FONTNAME',(1,i),(1,i),'Helvetica-Bold')
            t.setStyle(ts3); story.append(t)
        story.append(Spacer(1,8))
        story.append(Paragraph("Disclaimer: Model trained on synthetic data for demonstration only. Not for real academic decisions.", S['small']))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1,16))
    story.append(HRFlowable(width=W, thickness=0.5, color=MUTED))
    story.append(Spacer(1,5))
    story.append(Paragraph(f"EduTech Impact on AI · Report generated {now} · Built by Karunakar Reddy Pamireddy · github.com/Karunakarreddy-Pamireddy", S['small']))

    doc.build(story)
    buf.seek(0)
    return buf.read()
