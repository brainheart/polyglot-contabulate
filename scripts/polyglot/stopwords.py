"""Per-language function words suppressed in the Renderings view.

Keys are in the same normalization as textnorm.key(col, ...): Hebrew
consonantal, Greek/Latin folded, German/English lowercased. The UI lets the
reader switch suppression off.
"""

STOPWORDS = {
    "he": """
        את אשר על אל כי לא כל גם הנה או אם עד מן מה מי זה זאת הוא היא הם הן אני אתה אנכי אנחנו
        לו לי לה להם לך בו בה בם בי עם אתו אתם אותו אתך ויאמר ויהי והיה אמר ואת ועל ואל וכל כן לכן
        פן בין תחת אחרי לפני כאשר אך רק גם יש אין עוד שם אז ואשר ולא כי־אם לאמר
    """,
    "grc": """
        ο η το οι αι τα του της των τω τη τοις ταις τον την τους τας και δε γαρ ουν μεν τε
        εν εις εκ εξ απο προς επι δια κατα μετα περι παρα υπο υπερ ως οτι ινα μη ου ουκ ουχ αλλα
        αυτος αυτου αυτω αυτον αυτη αυτης αυτην αυτοι αυτων αυτοις αυτους αυτα αυτας
        εγω μου μοι με ημεις ημων ημιν ημας συ σου σοι σε υμεις υμων υμιν υμας
        ουτος τουτο ταυτα τουτου τουτω τουτον εκεινος ος ου ω ον ην ης αν εαν ει εστιν ην ειπεν λεγων
        πας παντα παντες παντων πασα πασης πασιν ιδου τις τι
    """,
    "la": """
        et in ad de ex e a ab cum per pro super sub non ne nec neque sed autem enim ergo vero quia quod
        ut si qui quae quod cuius cui quem quam quos quas quibus quorum est sunt erat erant fuit esse
        ego me mihi mei nos nobis tu te tibi vos vobis eius eis eum eam eos eas ei ea illi ille illa illud
        illum illos hic haec hoc huius his hi hunc hanc omnes omnis omnia omnium sicut quoniam dixit
        ait dicens tunc iam ecce atque ac sui suis suum suam sua se
    """,
    "de": """
        und der die das den dem des ein eine einen einem einer eines er sie es ich du wir ihr ihn ihm
        ihnen mich mir dich dir uns euch sein seine seinen seinem seiner seines ihre ihren ihrem ihrer
        in zu von mit auf an aus bei nach über unter vor für um durch wider gegen
        ist sind war waren wird werden ward hat haben hatte hatten sei soll sollen will wollen
        nicht auch aber denn daß da so wie als wenn was wer welche welcher alle allen aller alles
        sprach spricht sprachen siehe also doch noch nun hin her
    """,
    "en": """
        the and of to in that shall he unto i his a for they be is him not them it with all thou
        thy was which my me but ye their have thee from as are when this out were by upon you an
        or there so then on at had will hath us her into we she our your these those what who whom
        said saith say did do also even because if no nor let may might been being o
    """,
}


def as_sets():
    return {k: sorted(set(v.split())) for k, v in STOPWORDS.items()}
