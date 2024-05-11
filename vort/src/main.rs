#[derive(Clone, Eq, PartialEq)]
enum Orient {
    U,
    R,
    Tu,
    Tr,
}
impl std::fmt::Display for Orient {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Orient::U => write!(f, "U"),
            Orient::R => write!(f, "R"),
            Orient::Tu => write!(f, "Tu"),
            Orient::Tr => write!(f, "Tr"),
        }
    }
}

const LATEST_URL: &str = "https://www.unicode.org/Public/UCD/latest/ucd/VerticalOrientation.txt";
const SUPPORTED_URL: &str = "https://www.unicode.org/Public/15.1.0/ucd/VerticalOrientation.txt";
fn get_csv() -> String {
    let csv_supported = ureq::get(SUPPORTED_URL)
        .call()
        .unwrap()
        .into_string()
        .unwrap();
    let csv_latest = ureq::get(LATEST_URL).call().unwrap().into_string().unwrap();
    if csv_supported != csv_latest {
        eprintln!("WARNING: Supported VerticalOrientation is out of date")
    }
    csv_supported
}
fn get_csv_ranges() -> Vec<((u32, u32), Orient)> {
    let csv = get_csv();
    csv.lines()
        .filter_map(|cline| {
            cline
                .split('#')
                .next()
                .and_then(|x| {
                    let line = x.trim();
                    if !line.is_empty() {
                        let row: Vec<&str> = line.split(';').collect();
                        let or = match row[1].trim() {
                            "U" => Orient::U,
                            "R" => Orient::R,
                            "Tu" => Orient::Tu,
                            "Tr" => Orient::Tr,
                            _ => panic!(),
                        };
                        let rv: Vec<&str> = row[0].split("..").collect();
                        let rang = if rv.len() == 1 {
                            let rb = u32::from_str_radix(rv[0].trim(), 16).unwrap();
                            (rb, rb)
                        } else if rv.len() == 2 {
                            let rb = u32::from_str_radix(rv[0].trim(), 16).unwrap();
                            let re = u32::from_str_radix(rv[1].trim(), 16).unwrap();
                            (rb, re)
                        } else {
                            panic!();
                        };
                        Some((rang, or))
                    } else {
                        None
                    }
                })
        })
        .collect()
}

// Certain ranges of unassigned code points default to U.
// What's the point of the table? assign them ffs...
fn get_default_ranges() -> Vec<((u32, u32), Orient)> {
    vec![
        ((0x0, 0x10ffff), Orient::R),
        ((0x18b0, 0x18ff), Orient::U),
        ((0x2065, 0x2065), Orient::U),
        ((0x2150, 0x218f), Orient::U),
        ((0x2400, 0x245f), Orient::U),
        ((0x2bb8, 0x2bff), Orient::U),
        ((0x2e80, 0xa4cf), Orient::U),
        ((0xa960, 0xa97f), Orient::U),
        ((0xac00, 0xd7ff), Orient::U),
        ((0xe000, 0xfaff), Orient::U),
        ((0xfe10, 0xfe1f), Orient::U),
        ((0xfe50, 0xfe6f), Orient::U),
        ((0xffe7, 0xffe7), Orient::U),
        ((0xfff0, 0xfff8), Orient::U),
        ((0x11580, 0x115ff), Orient::U),
        ((0x11a00, 0x11aaf), Orient::U),
        ((0x13000, 0x1345f), Orient::U),
        ((0x14400, 0x1467f), Orient::U),
        ((0x16fe0, 0x18aff), Orient::U),
        ((0x18b00, 0x18d7f), Orient::U),
        ((0x1aff0, 0x1afff), Orient::U),
        ((0x1b100, 0x1b16f), Orient::U),
        ((0x1b170, 0x1b2ff), Orient::U),
        ((0x1cf00, 0x1cfcf), Orient::U),
        ((0x1d000, 0x1d1ff), Orient::U),
        ((0x1d2e0, 0x1d2ff), Orient::U),
        ((0x1d300, 0x1d37f), Orient::U),
        ((0x1d800, 0x1daaf), Orient::U),
        ((0x1f000, 0x1f0ff), Orient::U),
        ((0x1f100, 0x1f2ff), Orient::U),
        ((0x1f680, 0x1f7ff), Orient::U),
        ((0x1f900, 0x1f9ff), Orient::U),
        ((0x1fa00, 0x1faff), Orient::U),
        ((0x20000, 0x2fffd), Orient::U),
        ((0x30000, 0x3fffd), Orient::U),
        ((0xf0000, 0xffffd), Orient::U),
        ((0x100000, 0x10fffd), Orient::U),
    ]
}

fn get_ranges() -> Vec<((u32, u32), Orient)> {
    let mut res = vec![];
    res.extend(get_default_ranges());
    res.extend(get_csv_ranges());
    res
}

fn main() {
    let ranges = get_ranges();
    let mut map: rangemap::RangeInclusiveMap<u32, Orient> = rangemap::RangeInclusiveMap::new();
    for range in ranges {
        map.insert(((range.0).0)..=((range.0).1), range.1);
    }
    for (range, val) in map.iter() {
        println!("{:x} {:x} {}", range.start(), range.end(), val);
    }
}
